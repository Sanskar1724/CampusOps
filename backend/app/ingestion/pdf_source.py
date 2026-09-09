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
from backend.app.ingestion.extract import enrich_with_llm, extract_facts
from backend.app.memory import add_chunk

MAX_PDF_BYTES = 10 * 1024 * 1024
ALLOWED_MIME = {"application/pdf"}
CHUNK_CHARS = 1200


def extract_text(filename: str, mime: str, data: bytes) -> str:
    if mime == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return data.decode("utf-8", errors="ignore")


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
        raise ValueError("No readable text found in the document.")
    doc = models.Document(student_id=student_id, filename=filename, mime=mime,
                          size_bytes=len(data), is_demo=is_demo)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    for idx, piece in enumerate(chunk_text(text)):
        add_chunk(db, doc, idx, piece)
    subjects = student_subjects(db, student_id)
    facts = enrich_with_llm(text[:4000], extract_facts(text[:4000], subjects))
    doc.facts_json = json.dumps(facts)
    if facts.get("due_date"):
        due = datetime.fromisoformat(facts["due_date"]).replace(tzinfo=timezone.utc)
        db.add(models.Deadline(student_id=student_id, title=f"{filename}: {facts.get('kind')}",
                               subject=facts.get("subject", ""), due_at=due,
                               source="pdf", source_id=f"document:{doc.id}"))
    if facts.get("kind") in ("exam", "announcement", "academic_notice", "event"):
        db.add(models.Announcement(student_id=student_id, title=filename,
                                   body=facts.get("summary", text[:1000]),
                                   source="pdf", source_id=f"document:{doc.id}",
                                   priority=facts.get("priority", "normal")))
    db.commit()
    db.refresh(doc)
    return doc
