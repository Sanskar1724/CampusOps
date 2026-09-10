"""Change / conflict detection. New facts are compared against stored state;
conflicts keep provenance (source + timestamp) and are surfaced, never
silently overwritten."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models


def _already_notified(db: Session, student_id: int, source_id: str) -> bool:
    return db.scalar(select(models.Notification).where(
        models.Notification.student_id == student_id,
        models.Notification.thread_id == source_id)) is not None


def detect_schedule_change(db: Session, student_id: int, facts: dict, source_label: str) -> models.Notification | None:
    """Compare extracted room/time facts with the stored timetable."""
    subject = facts.get("subject")
    if not subject or facts.get("kind") not in ("room_change", "timetable_change"):
        return None
    entries = list(db.scalars(select(models.TimetableEntry).where(
        models.TimetableEntry.student_id == student_id,
        models.TimetableEntry.subject == subject)))
    if not entries:
        return None
    new_room = facts.get("new_room")
    changed = [e for e in entries if new_room and e.room and e.room != new_room]
    if not changed and not facts.get("date"):
        return None
    source_id = f"change:{source_label}"
    if _already_notified(db, student_id, source_id):
        return None
    entry = changed[0] if changed else entries[0]
    body = (f"Detected change for {subject} (from {source_label}): "
            f"stored room {entry.room or '—'} {entry.start_time}, "
            f"new info points to room {new_room or '—'}"
            + (f" on {facts['date']}" if facts.get("date") else "") + ".")
    db.add(models.Announcement(student_id=student_id, title=f"Schedule change: {subject}",
                               body=body, source="detector", source_id=source_id,
                               priority="high"))
    note = models.Notification(student_id=student_id, kind="change",
                               title=f"{subject} class changed", body=body,
                               thread_id=source_id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
