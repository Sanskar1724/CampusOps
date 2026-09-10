"""CampusOps Core Agent — the single intelligence layer.

One `handle_turn()` serves Caspian chat, web chat, and proactive jobs. It
retrieves only what the turn needs (profile → timetable → deadlines → exams →
updates → memory), then composes via the configured LLM. Raw chain-of-thought
never leaves; only the composed reply is returned.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.app import models
from backend.app.agents import onboarding, tools
from backend.app.agents.tools import Ctx, DAY_NAMES
from backend.app.llm import SYSTEM_BASE, get_llm
from backend.app.models import utcnow

from backend.app import config as _config  # noqa: E402  (kept for respond_to_text)


def respond_to_text(text: str) -> str:
    """Pre-DB fallback (also used by the offline foundation test)."""
    if text.strip().lower() == _config.HELLO_TRIGGER:
        return _config.HELLO_REPLY
    return _config.FALLBACK_REPLY


def _fmt_classes(classes: list[dict]) -> str:
    if not classes:
        return "none"
    return "; ".join(
        f"{c['subject']} {c['start']}-{c['end']} (Room {c['room'] or '—'})" for c in classes)


def _parse_reminder(text: str, now: datetime) -> tuple[str, datetime] | None:
    low = text.lower()
    if "remind" not in low:
        return None
    body = re.sub(r"(?i)remind me (to|about)?", "", text).strip() or "Follow up"
    day = now
    if "day after tomorrow" in low:
        day = now + timedelta(days=2)
    elif "tomorrow" in low:
        day = now + timedelta(days=1)
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", low)
    hour, minute = 9, 0
    if m:
        hour = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
        minute = int(m.group(2) or 0)
    when = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if when <= now:
        when += timedelta(days=1)
    return body[:900], when


def handle_turn(db: Session, student: models.Student, text: str,
                channel: str = "caspian", now: datetime | None = None) -> str:
    now = now or utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if not onboarding.is_done(student):
        return onboarding.advance(db, student, text)

    c = Ctx(db=db, student=student, now=now)
    low = text.lower()
    sections: list[str] = []

    wants = {
        "schedule": any(w in low for w in
                         ["class", "timetable", "schedule", "today", "tomorrow", "lecture", "next"]),
        "deadlines": any(w in low for w in
                         ["deadline", "assignment", "due", "submission", "submit"]),
        "exams": "exam" in low,
        "updates": any(w in low for w in
                       ["email", "mail", "important", "notice", "announcement", "update", "change"]),
        "docs": any(w in low for w in
                    ["document", "pdf", "search", "find", "notice", "rule"]),
        "plan": any(w in low for w in
                    ["focus", "plan", "priorit", "brief", "morning", "do today", "summary of today",
                     "do now", "what next", "right now"]),
    }

    reminder = _parse_reminder(text, now)
    if reminder:
        body, when = reminder
        created = tools.create_reminder(c, body, when)
        sections.append(f"Reminder set: '{created['remind_at']}' — {body}.")
    if ("add" in low or "create" in low) and any(w in low for w in ["task", "todo"]):
        title = re.sub(r"(?i)(add|create)\s+(a\s+)?(task|todo)\s*:?", "", text).strip() or text.strip()
        created = tools.create_task(c, title)
        sections.append(f"Task #{created['id']} created: {created['title']}.")

    if wants["plan"] or not any(wants.values()):
        plan = tools.generate_daily_plan(c)
        focus = tools.get_focus_now(c)
        sections.append(f"Today ({DAY_NAMES[now.weekday()]}): {_fmt_classes(plan['today'])}.")
        sections.append(f"Next class: {plan['next_class']['subject']} "
                        f"{plan['next_class']['start']} Room {plan['next_class']['room'] or '—'}"
                        if plan["next_class"] else "Next class: none scheduled.")
        dl = plan["deadlines"]
        if dl:
            ranked_lines = []
            for d in dl[:5]:
                _, label = tools.urgency_score(d, now)
                ranked_lines.append(f"{d['title']} (due {d['due']}) [{label}]")
            sections.append("Deadlines (ranked): " + "; ".join(ranked_lines) + ".")
        else:
            sections.append("Deadlines: none open.")
        ex = plan["exams"][:3]
        sections.append("Exams: " + ("; ".join(
            f"{e['subject']} at {e['at']}" for e in ex) if ex else "none scheduled."))
        imp = plan["important"][:3]
        sections.append("Important: " + ("; ".join(
            f"{i['title']} [{i['priority']}]" for i in imp) if imp else "nothing new."))
        sections.append(f"🎯 Do now: {focus['do_now']}")
    else:
        if wants["schedule"]:
            sections.append(f"Today: {_fmt_classes(tools.get_today_schedule(c))}.")
            if "tomorrow" in low or "week" in low:
                sections.append(f"Tomorrow: {_fmt_classes(tools.get_tomorrow_schedule(c))}.")
            nxt = tools.get_next_class(c)
            sections.append(f"Next: {nxt['subject']} {nxt['start']}" if nxt else "Next: none.")
        if wants["deadlines"]:
            dl = tools.get_upcoming_deadlines(c)
            sections.append("Deadlines: " + ("; ".join(
                f"{d['title']} (due {d['due']})" for d in dl) if dl else "none open."))
        if wants["exams"]:
            ex = tools.get_upcoming_exams(c)
            sections.append("Exams: " + ("; ".join(
                f"{e['subject']} at {e['at']}" for e in ex) if ex else "none scheduled."))
        if wants["updates"]:
            imp = tools.get_important_updates(c)
            sections.append("Updates: " + ("; ".join(
                f"{i['title']} [{i['priority']}]" for i in imp) if imp else "nothing new."))
        if wants["docs"]:
            hits = tools.search_documents(c, text)
            sections.append("Documents: " + ("; ".join(
                f"{h['filename']}: {h['text'][:200]}" for h in hits) if hits else "no matches."))
            mems = tools.search_memory(c, text)[:3]
            if mems:
                sections.append("Memory: " + "; ".join(f"{m['key']}: {m['value'][:200]}" for m in mems))

    profile = (f"Student: {student.full_name}, {student.department} Div-{student.division} "
               f"Batch-{student.batch}, Sem {student.semester}.")
    context = profile + "\n" + "\n".join(sections)
    return get_llm().complete(SYSTEM_BASE, text, context=context)
