"""Document pipeline: validate â†’ extract text (any format) â†’ chunk â†’ embed â†’
extract facts â†’ memory.

Two realities of college PDFs: (1) digital PDFs have a text layer â€” parsed
directly, layout mode first; (2) scanned/photo PDFs have image pages with a
broken or missing text layer â€” detected by `is_garbage_text` and re-read with
vision OCR (page raster + OpenRouter vision model, cached per upload).
PDF text is untrusted data: only facts/summaries are stored, and nothing
inside a document can change agent behavior."""

from __future__ import annotations

import base64
import io
import json
import os
import re
from datetime import datetime, timezone

import httpx
from pypdf import PdfReader
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.ingestion.email_source import student_subjects
from backend.app.ingestion.extract import (
    enrich_with_llm,
    garbage_score,
    is_garbage_text,
    scan_facts,
)
from backend.app.memory import add_chunk

MAX_PDF_BYTES = 15 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_DOC_BYTES = 5 * 1024 * 1024
OCR_MAX_PAGES = 4
PDF_MIME = "application/pdf"
IMAGE_MIME = {"image/png", "image/jpeg"}
TEXT_MIME = {"text/plain", "text/csv"}
DOC_MIME = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}
VISION_MODELS = ["nex-agi/nex-n2.5-pro:free", "nex-agi/nex-n2.5-mini:free"]
CHUNK_CHARS = 1200


def _layout_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text(extraction_mode="layout") or "")
        except Exception:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _vision_ocr_png(png: bytes) -> str:
    """One page image â†’ transcribed text via a free vision model."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("Vision OCR needs OPENAI_API_KEY (OpenRouter).")
    b64 = base64.b64encode(png).decode()
    last_error: Exception | None = None
    for model in [os.environ.get("VISION_MODEL", VISION_MODELS[0]), *VISION_MODELS[1:]]:
        try:
            resp = httpx.post(
                f"{os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')}"
                "/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "max_tokens": 2000, "messages": [{
                    "role": "user", "content": [
                        {"type": "text", "text": (
                            "Transcribe every word of this document page exactly, "
                            "keeping tables and lines in reading order. No commentary.")},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{b64}"}}]}]},
                timeout=120).json()
            if "choices" in resp:
                return resp["choices"][0]["message"]["content"]
            last_error = ValueError(str(resp.get("error", resp))[:200])
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Vision OCR failed: {last_error}")


def _ocr_pdf_pages(data: bytes) -> str:
    import pymupdf

    doc = pymupdf.open(stream=data, filetype="pdf")
    out = []
    for page in doc[:OCR_MAX_PAGES]:
        png = page.get_pixmap(dpi=150).tobytes("png")
        out.append(_vision_ocr_png(png))
    if len(doc) > OCR_MAX_PAGES:
        out.append(f"[only first {OCR_MAX_PAGES} of {len(doc)} pages scanned]")
    return "\n".join(out)


def _ocr_image_bytes(data: bytes) -> str:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        return pytesseract.image_to_string(Image.open(io.BytesIO(data)))
    except ImportError:
        pass
    import pymupdf

    kind = "jpg" if data[:2] == b"\xff\xd8" else "png"
    doc = pymupdf.open(stream=data, filetype=kind)
    return _vision_ocr_png(doc[0].get_pixmap(dpi=150).tobytes("png"))


def extract_pdf_text(data: bytes) -> tuple[str, str]:
    """Returns (text, method): text layer, or vision OCR when it's garbage."""
    text = _layout_text(data)
    if not is_garbage_text(text, len(data)):
        return text, "text-layer"
    try:
        return _ocr_pdf_pages(data), "vision-ocr"
    except Exception as exc:
        return text, f"ocr-failed:{exc}"[:200]


def extract_any_text(filename: str, mime: str, data: bytes) -> tuple[str, str]:
    """Unified extractor: pdf / txt / csv / xlsx / docx / png / jpg."""
    name = filename.lower()
    if mime == PDF_MIME or name.endswith(".pdf"):
        return extract_pdf_text(data)
    if name.endswith(".txt") or mime in TEXT_MIME:
        return data.decode("utf-8", errors="ignore"), "text"
    if name.endswith(".csv"):
        return data.decode("utf-8", errors="ignore"), "csv"
    if name.endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        lines = []
        for sheet in wb.worksheets:
            lines.append(f"# Sheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                lines.append(" | ".join("" if v is None else str(v) for v in row))
        return "\n".join(lines), "xlsx"
    if name.endswith(".docx"):
        from docx import Document as DocxDocument
        doc = DocxDocument(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts), "docx"
    if mime in IMAGE_MIME or name.endswith((".png", ".jpg", ".jpeg")):
        try:
            return _ocr_image_bytes(data), "image-ocr"
        except ValueError as exc:
            raise ValueError(str(exc))
    raise ValueError(
        "Unsupported file. Upload PDF, TXT, CSV, XLSX, DOCX, PNG, or JPG.")


def extract_text(filename: str, mime: str, data: bytes) -> str:
    text, _ = extract_any_text(filename, mime, data)
    return text


def ocr_pdf(data: bytes) -> str:
    """Public wrapper: force vision-OCR re-read of a PDF (second chance when
    the digital text layer exists but is too jumbled for row detection)."""
    return _ocr_pdf_pages(data)


def ocr_image(data: bytes) -> str:
    return _ocr_image_bytes(data)


def chunk_text(text: str, size: int = CHUNK_CHARS) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for para in paras:
        if len(current) + len(para) + 1 > size and current:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n{para}".strip()
    if current:
        chunks.append(current)
    return chunks or ([text[:size]] if text.strip() else [])


def ingest_document(db: Session, student_id: int, filename: str, mime: str,
                    data: bytes, is_demo: bool = False) -> models.Document:
    name = filename.lower()
    if mime == PDF_MIME or name.endswith(".pdf"):
        if len(data) > MAX_PDF_BYTES:
            raise ValueError("File exceeds the 15 MB limit.")
    elif mime in IMAGE_MIME or name.endswith((".png", ".jpg", ".jpeg")):
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("Image exceeds the 5 MB limit.")
    elif len(data) > MAX_DOC_BYTES:
        raise ValueError("File exceeds the 5 MB limit.")
    text, method = extract_any_text(filename, mime, data)
    if not text.strip():
        raise ValueError("No readable text found in the document.")
    if is_garbage_text(text, len(data)) and method == "text-layer":
        raise ValueError(
            "This looks like a scanned PDF whose text is unreadable, and vision OCR "
            "is unavailable right now. Try again in a bit, or export a text version "
            "from your college portal.")
    doc = models.Document(student_id=student_id, filename=filename, mime=mime,
                          size_bytes=len(data), is_demo=is_demo)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    for idx, piece in enumerate(chunk_text(text)):
        if garbage_score(piece) > 0.5:
            continue  # never embed glyph salad
        add_chunk(db, doc, idx, piece)
    subjects = student_subjects(db, student_id)
    facts = enrich_with_llm(text[:8000], scan_facts(text[:12000], subjects))
    facts["extraction"] = method
    doc.facts_json = json.dumps(facts)
    made_deadline = False
    for item in facts.get("items", []):
        if item.get("kind") in ("assignment", "deadline") and item.get("date"):
            due = datetime.fromisoformat(item["date"]).replace(tzinfo=timezone.utc)
            db.add(models.Deadline(
                student_id=student_id, title=f"{filename}: {item['text'][:200]}",
                subject=item.get("subject", ""), due_at=due,
                source="pdf", source_id=f"document:{doc.id}"))
            made_deadline = True
    if facts.get("due_date") and not made_deadline:
        due = datetime.fromisoformat(facts["due_date"]).replace(tzinfo=timezone.utc)
        db.add(models.Deadline(student_id=student_id, title=f"{filename}: {facts.get('kind')}",
                               subject=facts.get("subject", ""), due_at=due,
                               source="pdf", source_id=f"document:{doc.id}"))
    if facts.get("kind") in ("exam", "announcement", "academic_notice", "event"):
        db.add(models.Announcement(student_id=student_id, title=filename,
                                   body=facts.get("summary", text[:1000]),
                                   source="pdf", source_id=f"document:{doc.id}",
                                   priority=facts.get("priority", "normal")))
    if facts.get("dates") and facts["kind"] == "exam" and facts.get("subjects"):
        when = datetime.fromisoformat(facts["dates"][0]).replace(tzinfo=timezone.utc)
        db.add(models.Exam(student_id=student_id, subject=facts["subjects"][0],
                           title=filename, exam_at=when,
                           room=(facts.get("rooms") or [""])[0], source="pdf"))
    db.commit()
    db.refresh(doc)
    return doc
