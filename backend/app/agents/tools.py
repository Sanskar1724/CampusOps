"""Agent tools. Each tool reads only the current student's rows and returns
plain data; the Core Agent decides what to call and the LLM composes the
answer. No chain-of-thought ever leaves the server."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.memory import semantic_search
from backend.app.models import utcnow

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class Ctx:
    db: Session
    student: models.Student
    now: datetime


def _applies(entry: models.TimetableEntry, student: models.Student) -> bool:
    if entry.division and student.division and entry.division != student.division:
        return False
    if entry.batch and student.batch and entry.batch != student.batch:
        return False
    return True


def _fmt(entries: list[models.TimetableEntry]) -> list[dict]:
    return [{"subject": e.subject, "day": DAY_NAMES[e.day], "start": e.start_time,
             "end": e.end_time, "room": e.room, "faculty": e.faculty} for e in entries]


def get_day_schedule(c: Ctx, day: int) -> list[dict]:
    rows = list(c.db.scalars(select(models.TimetableEntry).where(
        models.TimetableEntry.student_id == c.student.id,
        models.TimetableEntry.day == day).order_by(models.TimetableEntry.start_time)))
    return _fmt([e for e in rows if _applies(e, c.student)])


def get_today_schedule(c: Ctx) -> list[dict]:
    return get_day_schedule(c, c.now.weekday())


def get_tomorrow_schedule(c: Ctx) -> list[dict]:
    return get_day_schedule(c, (c.now.weekday() + 1) % 7)


def get_week_schedule(c: Ctx) -> dict:
    return {DAY_NAMES[d]: get_day_schedule(c, d) for d in range(7)}


def get_next_class(c: Ctx) -> dict | None:
    today = get_today_schedule(c)
    now_hm = c.now.strftime("%H:%M")
    for cls in today:
        if cls["start"] > now_hm:
            return cls
    for offset in range(1, 8):
        day = (c.now.weekday() + offset) % 7
        classes = get_day_schedule(c, day)
        if classes:
            return classes[0]
    return None


def get_upcoming_deadlines(c: Ctx, days: int = 14) -> list[dict]:
    rows = list(c.db.scalars(select(models.Deadline).where(
        models.Deadline.student_id == c.student.id,
        models.Deadline.status == "open").order_by(models.Deadline.due_at)))
    out = []
    for d in rows:
        if d.due_at and d.due_at.replace(tzinfo=timezone.utc) > c.now + timedelta(days=days):
            continue
        out.append({"id": d.id, "title": d.title, "subject": d.subject,
                    "due": d.due_at.isoformat() if d.due_at else None,
                    "priority": d.priority, "source": d.source})
    return out


def get_upcoming_exams(c: Ctx, days: int = 30) -> list[dict]:
    rows = list(c.db.scalars(select(models.Exam).where(
        models.Exam.student_id == c.student.id).order_by(models.Exam.exam_at)))
    return [{"subject": e.subject, "title": e.title,
             "at": e.exam_at.isoformat() if e.exam_at else None, "room": e.room}
            for e in rows
            if not e.exam_at or e.exam_at.replace(tzinfo=timezone.utc) >= c.now - timedelta(days=1)][:20]


def get_important_updates(c: Ctx, limit: int = 10) -> list[dict]:
    rows = list(c.db.scalars(select(models.Announcement).where(
        models.Announcement.student_id == c.student.id)
        .order_by(models.Announcement.created_at.desc()).limit(limit * 2)))
    high = [a for a in rows if a.priority == "high"]
    rest = [a for a in rows if a.priority != "high"]
    return [{"title": a.title, "body": a.body[:500], "priority": a.priority,
             "source": a.source} for a in (high + rest)[:limit]]


def search_emails(c: Ctx, query: str, limit: int = 5) -> list[dict]:
    q = query.lower()
    rows = list(c.db.scalars(select(models.Email).where(
        models.Email.student_id == c.student.id)
        .order_by(models.Email.received_at.desc()).limit(50)))
    hits = [e for e in rows if q in f"{e.subject} {e.body}".lower()][:limit]
    return [{"subject": e.subject, "sender": e.sender, "body": e.body[:600],
             "received": e.received_at.isoformat()} for e in hits]


def search_documents(c: Ctx, query: str, top_k: int = 5) -> list[dict]:
    return semantic_search(c.db, c.student.id, query, top_k=top_k)


def search_memory(c: Ctx, query: str) -> list[dict]:
    mems = list(c.db.scalars(select(models.Memory).where(
        models.Memory.student_id == c.student.id)))
    q = query.lower()
    hits = [{"type": m.mem_type, "key": m.key, "value": m.value, "source": m.source}
            for m in mems if q in f"{m.key} {m.value}".lower()][:5]
    return hits + [{"type": "document", "key": h["filename"], "value": h["text"][:400],
                    "source": "semantic"}
                   for h in search_documents(c, query, top_k=3)]


def get_tasks(c: Ctx) -> list[dict]:
    rows = list(c.db.scalars(select(models.Task).where(
        models.Task.student_id == c.student.id,
        models.Task.status == "open").order_by(models.Task.created_at.desc())))
    return [{"id": t.id, "title": t.title, "detail": t.detail,
             "due": t.due_at.isoformat() if t.due_at else None} for t in rows]


def create_task(c: Ctx, title: str, detail: str = "") -> dict:
    task = models.Task(student_id=c.student.id, title=title[:480], detail=detail[:2000])
    c.db.add(task)
    c.db.commit()
    c.db.refresh(task)
    return {"id": task.id, "title": task.title}


def create_reminder(c: Ctx, text: str, remind_at: datetime) -> dict:
    reminder = models.Reminder(student_id=c.student.id, text=text[:900], remind_at=remind_at)
    c.db.add(reminder)
    c.db.commit()
    c.db.refresh(reminder)
    return {"id": reminder.id, "remind_at": reminder.remind_at.isoformat()}


def list_reminders(c: Ctx) -> list[dict]:
    rows = list(c.db.scalars(select(models.Reminder).where(
        models.Reminder.student_id == c.student.id,
        models.Reminder.status == "pending").order_by(models.Reminder.remind_at)))
    return [{"id": r.id, "text": r.text, "at": r.remind_at.isoformat()} for r in rows]


def generate_daily_plan(c: Ctx) -> dict:
    return {"today": get_today_schedule(c), "next_class": get_next_class(c),
            "deadlines": get_upcoming_deadlines(c, days=7),
            "exams": get_upcoming_exams(c, days=14),
            "important": get_important_updates(c, limit=5),
            "tasks": get_tasks(c)}
