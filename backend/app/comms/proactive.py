"""Proactive delivery through the hosted gateway.

Uses the same endpoint the SDK itself maps `Post` to
(`POST /v1/conversations/{id}/messages`), with the conversation id taken from
the stored hosted thread id (`channel:conversation-id`). Outcomes are recorded
on the `notifications` row — queued when unconfigured, sent/failed otherwise.
"""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from backend.app import config, models
from backend.app.models import utcnow


def conversation_id(thread_id: str) -> str:
    parts = str(thread_id).split(":", 1)
    return parts[1] if len(parts) > 1 else str(thread_id)


def queue_notification(db: Session, student_id: int, kind: str, title: str, body: str,
                       thread_id: str = "") -> models.Notification:
    note = models.Notification(student_id=student_id, kind=kind, title=title[:480],
                               body=body, thread_id=thread_id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def deliver_queued(db: Session, note: models.Notification) -> models.Notification:
    """Attempt one delivery. Returns the updated row (sent/failed/queued)."""
    thread_id = note.thread_id or (db.get(models.Student, note.student_id).caspian_thread_id or "")
    if not config.CASPIAN_API_KEY or not thread_id:
        note.status = "queued"
        db.commit()
        return note
    try:
        resp = httpx.post(
            f"{config.CASPIAN_BASE_URL}/v1/conversations/{conversation_id(thread_id)}/messages",
            headers={"Authorization": f"Bearer {config.CASPIAN_API_KEY}"},
            json={"text": f"{note.title}\n\n{note.body}"},
            timeout=30)
        resp.raise_for_status()
        note.status = "sent"
        note.sent_at = utcnow()
    except Exception as exc:
        note.status = "failed"
        note.body = f"{note.body}\n[delivery error: {exc}]"[:4000]
    db.commit()
    db.refresh(note)
    return note


def notify_student(db: Session, student_id: int, kind: str, title: str, body: str) -> models.Notification:
    student = db.get(models.Student, student_id)
    note = queue_notification(db, student_id, kind, title, body,
                              thread_id=(student.caspian_thread_id or "") if student else "")
    return deliver_queued(db, note)
