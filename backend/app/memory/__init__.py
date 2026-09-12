"""Layered memory access. Structured tables are authoritative; chunks give
semantic recall. Everything is student-scoped at the query level."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import embeddings, models
from backend.app.models import utcnow


def save_memory(db: Session, student_id: int, mem_type: str, key: str, value: str,
                source: str = "chat", confidence: float = 1.0) -> models.Memory:
    existing = db.scalar(select(models.Memory).where(
        models.Memory.student_id == student_id,
        models.Memory.mem_type == mem_type, models.Memory.key == key))
    if existing:
        existing.value = value
        existing.source = source
        existing.confidence = confidence
        existing.updated_at = utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    mem = models.Memory(student_id=student_id, mem_type=mem_type, key=key,
                        value=value, source=source, confidence=confidence)
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem


def get_memories(db: Session, student_id: int, mem_type: str | None = None):
    q = select(models.Memory).where(models.Memory.student_id == student_id)
    if mem_type:
        q = q.where(models.Memory.mem_type == mem_type)
    return list(db.scalars(q.order_by(models.Memory.updated_at.desc())))


def add_chunk(db: Session, document: models.Document, idx: int, text: str) -> models.DocumentChunk:
    chunk = models.DocumentChunk(document_id=document.id, student_id=document.student_id,
                                 idx=idx, text=text,
                                 embedding_json=embeddings.dumps(embeddings.embed(text)))
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def _token_overlap(query: str, text: str) -> float:
    """Keyword recall: fraction of meaningful query tokens present in the text."""
    qtokens = {t for t in embeddings.tokens(query) if len(t) > 2}
    if not qtokens:
        return 0.0
    text_tokens = set(embeddings.tokens(text))
    return len(qtokens & text_tokens) / len(qtokens)


def semantic_search(db: Session, student_id: int, query: str, top_k: int = 5):
    from backend.app.ingestion.extract import garbage_score  # noqa: E402
    chunks = list(db.scalars(select(models.DocumentChunk).where(
        models.DocumentChunk.student_id == student_id)))
    if not chunks:
        return []
    q = embeddings.embed(query)
    scored = []
    for chunk in chunks:
        if garbage_score(chunk.text) > 0.5:
            continue  # glyph salad never answers anything
        vec_score = embeddings.cosine(q, embeddings.loads(chunk.embedding_json))
        # Hybrid: embedding similarity + keyword recall. Either signal alone
        # can surface the right chunk; together they rank precisely.
        score = round(0.5 * vec_score + 0.5 * _token_overlap(query, chunk.text), 4)
        doc = db.get(models.Document, chunk.document_id)
        scored.append({"chunk_id": chunk.id, "document_id": chunk.document_id,
                       "filename": doc.filename if doc else "",
                       "text": chunk.text, "score": score})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def get_or_create_conversation(db: Session, *, channel: str,
                               thread_id: str | None = None,
                               sender: str | None = None,
                               student_id: int | None = None) -> models.Conversation:
    conv = None
    if thread_id:
        conv = db.scalar(select(models.Conversation).where(
            models.Conversation.caspian_thread_id == thread_id))
    if conv is None:
        conv = models.Conversation(channel=channel, caspian_thread_id=thread_id,
                                   caspian_sender=sender, student_id=student_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
    else:
        touched = False
        if student_id and conv.student_id is None:
            conv.student_id = student_id
            touched = True
        if sender and not conv.caspian_sender:
            conv.caspian_sender = sender
            touched = True
        if touched:
            conv.updated_at = utcnow()
            db.commit()
            db.refresh(conv)
    return conv


def log_message(db: Session, conversation_id: int, role: str, text: str) -> None:
    db.add(models.ChatMessage(conversation_id=conversation_id, role=role, text=text[:4000]))
    db.commit()
