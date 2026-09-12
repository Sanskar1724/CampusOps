"""Proactive delivery: hosted gateway first, Telegram Bot API as fallback.

The gateway needs clean TLS to api.trycaspianai.com, which some networks
block. Telegram's Bot API usually stays reachable, so once a student has
messaged the bot (their chat id is captured in `handlers`), notifications
can still go out that way. Outcomes are recorded on the `notifications`
row — queued when nothing is configured, sent/failed otherwise. Failures
store a short `error`, never rewriting the message body."""

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


def _send_via_gateway(thread_id: str, text: str) -> None:
    resp = httpx.post(
        f"{config.CASPIAN_BASE_URL}/v1/conversations/{conversation_id(thread_id)}/messages",
        headers={"Authorization": f"Bearer {config.CASPIAN_API_KEY}"},
        json={"text": text},
        timeout=30)
    resp.raise_for_status()


def _send_via_telegram(chat_id: str, text: str) -> None:
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("no Telegram bot token configured")
    resp = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat_id, "text": text[:4000]}, timeout=30)
    resp.raise_for_status()
    if not resp.json().get("ok"):
        raise ValueError(f"Telegram refused the message: {resp.text[:160]}")


def deliver_queued(db: Session, note: models.Notification) -> models.Notification:
    """Attempt one delivery. Returns the updated row (sent/failed/queued)."""
    student = db.get(models.Student, note.student_id)
    thread_id = note.thread_id or ((student.caspian_thread_id or "") if student else "")
    text = f"{note.title}\n\n{note.body}"
    errors: list[str] = []
    if config.CASPIAN_API_KEY and thread_id:
        try:
            _send_via_gateway(thread_id, text)
            note.status = "sent"
            note.sent_at = utcnow()
            note.error = ""
            db.commit()
            db.refresh(note)
            return note
        except Exception as exc:
            errors.append(f"gateway: {exc}"[:220])
    chat_id = (student.telegram_chat_id or "") if student else ""
    if chat_id:
        try:
            _send_via_telegram(chat_id, text)
            note.status = "sent"
            note.sent_at = utcnow()
            note.error = ""
            db.commit()
            db.refresh(note)
            return note
        except Exception as exc:
            errors.append(f"telegram: {exc}"[:220])
    if not errors:
        note.status = "queued"
        note.error = ""
    else:
        note.status = "failed"
        note.error = " | ".join(errors)[:480]
    db.commit()
    db.refresh(note)
    return note


def notify_student(db: Session, student_id: int, kind: str, title: str, body: str) -> models.Notification:
    student = db.get(models.Student, student_id)
    note = queue_notification(db, student_id, kind, title, body,
                              thread_id=(student.caspian_thread_id or "") if student else "")
    return deliver_queued(db, note)
