"""Scheduled intelligence: morning brief, deadline/reminder sweeps, queued
delivery. Content is rendered from retrieved facts with templates (no
hallucinated times or rooms); spam is capped by per-item dedupe records."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.agents.tools import (
    generate_daily_plan,
    get_day_schedule,
    get_focus_now,
    make_ctx,
    urgency_score,
)
from backend.app.comms.proactive import deliver_queued, notify_student, queue_notification
from backend.app.models import utcnow

BRIEF_EMOJI = "ðŸŒ…"


def _countdown(due_raw: str | None, now: datetime) -> str:
    if not due_raw:
        return "no date"
    try:
        due = datetime.fromisoformat(str(due_raw))
    except (ValueError, TypeError):
        return str(due_raw)
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    delta = due - now
    if delta.total_seconds() < 0:
        return "ðŸ”´ OVERDUE"
    hours = int(delta.total_seconds() // 3600)
    if hours < 24:
        return f"ðŸŸ  in {hours}h"
    return f"ðŸŸ¡ in {hours // 24}d"


def build_daily_brief(db: Session, student: models.Student, now: datetime) -> tuple[str, str]:
    plan = generate_daily_plan(make_ctx(db=db, student=student, now=now))
    focus = get_focus_now(make_ctx(db=db, student=student, now=now))
    lines = [f"GOOD MORNING {BRIEF_EMOJI} {student.full_name or 'there'} â€” here's your day", "",
             "ðŸ—“ï¸ Today's classes:"]
    if plan["today"]:
        for c in plan["today"]:
            lines.append(f"- {c['start']} {c['subject']} (Room {c['room'] or 'â€”'})")
    else:
        lines.append("- No classes scheduled. Perfect revision day.")
    lines.append("")
    if plan["deadlines"]:
        lines.append("â° Deadlines (ranked by urgency):")
        for d in plan["deadlines"][:4]:
            _, label = urgency_score(d, now)
            lines.append(f"- {d['title']} â€” due {d['due']} [{label} {_countdown(d['due'], now)}]")
        lines.append("")
    if plan["important"]:
        lines.append("ðŸš¨ Important:")
        for i in plan["important"][:3]:
            lines.append(f"- {i['title']} [{i['priority']}]")
        lines.append("")
    if plan["deadlines"]:
        lines.append("ðŸŽ¯ Do NOW:")
        lines.append(f"- {focus['do_now']}")
    else:
        lines.append("ðŸŽ¯ No urgent deadlines â€” a good day to revise ahead 30 min.")
    lines.append("")
    lines.append("Ask me anything in chat â€” I answer from your timetable, inbox & docs.")
    return "Your daily brief ðŸŒ…", "\n".join(lines)


def _recent_notification(db: Session, student_id: int, kind: str, since: datetime) -> bool:
    return db.scalar(select(models.Notification).where(
        models.Notification.student_id == student_id,
        models.Notification.kind == kind,
        models.Notification.created_at >= since)) is not None


def run_daily_brief(db: Session, now: datetime) -> int:
    from backend.app.api.deps import get_prefs, in_quiet_hours, kind_allowed
    sent = 0
    students = list(db.scalars(select(models.Student).where(
        models.Student.onboarding_status == "done")))
    for student in students:
        prefs = get_prefs(db, student.id)
        if not kind_allowed(prefs, "brief") or in_quiet_hours(prefs, now):
            continue
        if _recent_notification(db, student.id, "brief", now - timedelta(hours=20)):
            continue
        title, body = build_daily_brief(db, student, now)
        notify_student(db, student.id, "brief", title, body)
        sent += 1
    return sent


def run_reminder_sweep(db: Session, now: datetime) -> int:
    from backend.app.api.deps import get_prefs, in_quiet_hours, kind_allowed
    due = list(db.scalars(select(models.Reminder).where(
        models.Reminder.status == "pending", models.Reminder.remind_at <= now)))
    fired = 0
    for reminder in due:
        prefs = get_prefs(db, reminder.student_id)
        if not kind_allowed(prefs, "reminder") or in_quiet_hours(prefs, now):
            continue  # stays pending — delivered on a later sweep
        notify_student(db, reminder.student_id, "reminder", "Reminder", reminder.text)
        reminder.status = "sent"
        db.commit()
        fired += 1
    return fired


def run_deadline_sweep(db: Session, now: datetime) -> int:
    from backend.app.api.deps import get_prefs, in_quiet_hours, kind_allowed
    horizon = now + timedelta(hours=24)
    rows = list(db.scalars(select(models.Deadline).where(
        models.Deadline.status == "open", models.Deadline.due_at != None,  # noqa: E711
        models.Deadline.due_at <= horizon)))
    sent = 0
    for deadline in rows:
        prefs = get_prefs(db, deadline.student_id)
        if not kind_allowed(prefs, "deadline") or in_quiet_hours(prefs, now):
            continue  # no marker written — fires on a later sweep
        marker = f"deadline:{deadline.id}"
        if db.scalar(select(models.Notification).where(
                models.Notification.student_id == deadline.student_id,
                models.Notification.thread_id == marker)):
            continue
        note = queue_notification(db, deadline.student_id, "deadline",
                                  f"Due soon: {deadline.title}",
                                  f"{deadline.subject}: due {deadline.due_at}.",
                                  thread_id=marker)
        deliver_queued(db, note)
        sent += 1
    return sent


def run_delivery_retry(db: Session, limit: int = 50) -> int:
    queued = list(db.scalars(select(models.Notification).where(
        models.Notification.status == "queued").order_by(
        models.Notification.created_at).limit(limit)))
    for note in queued:
        deliver_queued(db, note)
    return len(queued)


def run_class_soon_sweep(db: Session, now: datetime, minutes: int = 15) -> int:
    """'Class starting soon' nudges — the heart of Telegram alerts.

    Any visible class starting within the next `minutes` gets one notification
    (per class per day marker, so it never repeats). Respects kind toggle
    (deadline pref family) and quiet hours like every other sweep."""
    from backend.app.agents.tools import make_ctx
    from backend.app.api.deps import get_prefs, in_quiet_hours, kind_allowed
    sent = 0
    students = list(db.scalars(select(models.Student).where(
        models.Student.onboarding_status == "done")))
    for student in students:
        prefs = get_prefs(db, student.id)
        if not kind_allowed(prefs, "reminder") or in_quiet_hours(prefs, now):
            continue
        c = make_ctx(db=db, student=student, now=now)
        today = c.now.weekday()
        for cls in get_day_schedule(c, today):
            try:
                start = datetime.combine(c.now.date(),
                                         datetime.strptime(cls["start"], "%H:%M").time())
            except (ValueError, KeyError):
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            delta_min = (start - now).total_seconds() / 60
            if 0 <= delta_min <= minutes:
                marker = f"class:{student.id}:{today}:{cls['subject']}:{cls['start']}"
                if db.scalar(select(models.Notification).where(
                        models.Notification.student_id == student.id,
                        models.Notification.thread_id == marker)):
                    continue
                note = queue_notification(
                    db, student.id, "reminder",
                    f"🔔 {cls['subject']} starts at {cls['start']}",
                    f"Room {cls['room'] or '—'}"
                    + (f" · {cls['faculty']}" if cls.get("faculty") else "")
                    + ". Reply here if plans changed.",
                    thread_id=marker)
                deliver_queued(db, note)
                sent += 1
    return sent


def run_exam_sweep(db: Session, now: datetime, hours: int = 48) -> int:
    """Exam coming up within `hours` → one alert per exam (marker dedupe)."""
    horizon = now + timedelta(hours=hours)
    rows = list(db.scalars(select(models.Exam).where(
        models.Exam.exam_at != None,  # noqa: E711
        models.Exam.exam_at <= horizon)))
    sent = 0
    for exam in rows:
        if exam.exam_at.replace(tzinfo=timezone.utc) < now - timedelta(hours=2):
            continue
        marker = f"exam:{exam.id}"
        if db.scalar(select(models.Notification).where(
                models.Notification.student_id == exam.student_id,
                models.Notification.thread_id == marker)):
            continue
        from backend.app.api.deps import get_prefs, in_quiet_hours, kind_allowed
        prefs = get_prefs(db, exam.student_id)
        if not kind_allowed(prefs, "deadline") or in_quiet_hours(prefs, now):
            continue
        note = queue_notification(
            db, exam.student_id, "deadline",
            f"📝 Exam soon: {exam.subject}",
            f"{exam.subject} — {exam.title} at {exam.exam_at}"
            + (f" · Room {exam.room}" if exam.room else "") + ". Good luck! 🍀",
            thread_id=marker)
        deliver_queued(db, note)
        sent += 1
    return sent


def run_all(db: Session, now: datetime | None = None) -> dict:
    now = now or utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return {"briefs": run_daily_brief(db, now),
            "reminders": run_reminder_sweep(db, now),
            "deadlines": run_deadline_sweep(db, now),
            "class_soon": run_class_soon_sweep(db, now),
            "exams": run_exam_sweep(db, now),
            "retries": run_delivery_retry(db)}
