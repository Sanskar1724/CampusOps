"""Scheduled intelligence: morning brief, deadline/reminder sweeps, queued
delivery. Content is rendered from retrieved facts with templates (no
hallucinated times or rooms); spam is capped by per-item dedupe records."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.agents.tools import Ctx, generate_daily_plan
from backend.app.comms.proactive import deliver_queued, notify_student
from backend.app.models import utcnow

BRIEF_EMOJI = "👋"


def build_daily_brief(db: Session, student: models.Student, now: datetime) -> tuple[str, str]:
    plan = generate_daily_plan(Ctx(db=db, student=student, now=now))
    lines = [f"GOOD MORNING {BRIEF_EMOJI} {student.full_name or 'there'}", "",
             "Today's classes:"]
    if plan["today"]:
        for c in plan["today"]:
            lines.append(f"- {c['start']} {c['subject']} (Room {c['room'] or '—'})")
    else:
        lines.append("- No classes scheduled.")
    lines.append("")
    if plan["deadlines"]:
        lines.append("Upcoming:")
        for d in plan["deadlines"][:4]:
            lines.append(f"- {d['title']} (due {d['due']})")
        lines.append("")
    if plan["important"]:
        lines.append("Important:")
        for i in plan["important"][:3]:
            lines.append(f"- {i['title']}")
        lines.append("")
    if plan["deadlines"]:
        lines.append("Priority:")
        for n, d in enumerate(plan["deadlines"][:3], 1):
            lines.append(f"{n}. {d['title']}")
    else:
        lines.append("No urgent deadlines — good day to revise ahead.")
    return "Your daily brief", "\n".join(lines)


def _recent_notification(db: Session, student_id: int, kind: str, since: datetime) -> bool:
    return db.scalar(select(models.Notification).where(
        models.Notification.student_id == student_id,
        models.Notification.kind == kind,
        models.Notification.created_at >= since)) is not None


def run_daily_brief(db: Session, now: datetime) -> int:
    sent = 0
    students = list(db.scalars(select(models.Student).where(
        models.Student.onboarding_status == "done")))
    for student in students:
        if _recent_notification(db, student.id, "brief", now - timedelta(hours=20)):
            continue
        title, body = build_daily_brief(db, student, now)
        notify_student(db, student.id, "brief", title, body)
        sent += 1
    return sent


def run_reminder_sweep(db: Session, now: datetime) -> int:
    due = list(db.scalars(select(models.Reminder).where(
        models.Reminder.status == "pending", models.Reminder.remind_at <= now)))
    for reminder in due:
        notify_student(db, reminder.student_id, "reminder", "Reminder", reminder.text)
        reminder.status = "sent"
        db.commit()
    return len(due)


def run_deadline_sweep(db: Session, now: datetime) -> int:
    horizon = now + timedelta(hours=24)
    rows = list(db.scalars(select(models.Deadline).where(
        models.Deadline.status == "open", models.Deadline.due_at != None,  # noqa: E711
        models.Deadline.due_at <= horizon)))
    sent = 0
    for deadline in rows:
        marker = f"deadline:{deadline.id}"
        if db.scalar(select(models.Notification).where(
                models.Notification.student_id == deadline.student_id,
                models.Notification.thread_id == marker)):
            continue
        note = notify_student(db, deadline.student_id, "deadline",
                              f"Due soon: {deadline.title}",
                              f"{deadline.subject}: due {deadline.due_at}.")
        note.thread_id = marker
        db.commit()
        sent += 1
    return sent


def run_delivery_retry(db: Session, limit: int = 50) -> int:
    queued = list(db.scalars(select(models.Notification).where(
        models.Notification.status == "queued").order_by(
        models.Notification.created_at).limit(limit)))
    for note in queued:
        deliver_queued(db, note)
    return len(queued)


def run_all(db: Session, now: datetime | None = None) -> dict:
    now = now or utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return {"briefs": run_daily_brief(db, now),
            "reminders": run_reminder_sweep(db, now),
            "deadlines": run_deadline_sweep(db, now),
            "retries": run_delivery_retry(db)}
