"""Document pipeline: validate → extract text → chunk → embed → extract facts →
memory. PDF text is untrusted data: only facts/summaries are stored, and
nothing inside a document can change agent behavior."""

from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone

from pypdf import PdfReader
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.ingestion.email_source import student_subjects
from backend.app.ingestion.extract import enrich_with_llm, scan_facts
from backend.app.memory import add_chunk

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_MIME = {"application/pdf"}
ALLOWED_IMAGE_MIME = {"image/png", "image/jpeg"}
CHUNK_CHARS = 1200


def extract_text(filename: str, mime: str, data: bytes) -> str:
    if mime == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if mime in ALLOWED_IMAGE_MIME:
        return ocr_image(data)
    return data.decode("utf-8", errors="ignore")


def ocr_image(data: bytes) -> str:
    """Image text when an OCR engine exists; otherwise a clear error.

    Tesseract is optional: install the binary + `pip install pytesseract` and
    image uploads light up with zero code changes."""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        raise ValueError(
            "This photo has no readable text layer and no OCR engine is installed. "
            "Please upload the PDF version (or a CSV/JSON timetable) instead.")
    try:
        return pytesseract.image_to_string(Image.open(io.BytesIO(data)))
    except Exception as exc:
        raise ValueError(f"OCR failed: {exc}")


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
    if mime not in ALLOWED_MIME:
        raise ValueError(f"Only PDF uploads are supported (got {mime}).")
    if len(data) > MAX_PDF_BYTES:
        raise ValueError("File exceeds the 10 MB limit.")
    text = extract_text(filename, mime, data)
    if not text.strip():
        raise ValueError(
            "No readable text found. If this is a scanned/image-only PDF, "
            "export a text version from your college portal and upload that.")
    doc = models.Document(student_id=student_id, filename=filename, mime=mime,
                          size_bytes=len(data), is_demo=is_demo)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    for idx, piece in enumerate(chunk_text(text)):
        add_chunk(db, doc, idx, piece)
    subjects = student_subjects(db, student_id)
    facts = enrich_with_llm(text[:8000], scan_facts(text[:12000], subjects))
    doc.facts_json = json.dumps(facts)
    made_deadline = False
    for item in facts.get("items", []):
        if item.get("kind") in ("assignment", "deadline") and item.get("date"):
            due = datetime.fromisoformat(item["date"]).replace(tzinfo=timezone.utc)
            db.add(models.Deadline(
                student_id=student_id, title=f"{filename}: {item['text'][:200]}",
                subject=item.get("subject", ""), due_at=due,
                source="pdf", source_id=f"document:{doc.id}:{len(facts.get('items', []))}"))
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
