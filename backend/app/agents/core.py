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
from backend.app.agents.tools import DAY_NAMES, make_ctx
from backend.app.api.deps import get_user_context, set_pref
from backend.app.llm import SYSTEM_BASE, get_llm
from backend.app.models import utcnow
from backend.app.user_guide import GUIDE_POINTER

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
    if "remind me" not in low:
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


_DAY_ALIASES = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}


def _known_subjects(db, student_id: int) -> list[str]:
    from sqlalchemy import select as _select
    rows = db.scalars(_select(models.TimetableEntry.subject).where(
        models.TimetableEntry.student_id == student_id).distinct())
    return [r for r in rows if r]


def _find_day(low: str) -> int | None:
    for name, num in _DAY_ALIASES.items():
        if re.search(rf"\b{name}s?\b", low):
            return num
    return None


def _find_subject(low: str, subjects: list[str]) -> str | None:
    for subj in sorted(subjects, key=len, reverse=True):
        if subj and subj.lower() in low:
            return subj
    return None


def _handle_visibility(db, student, text: str, subjects: list[str]) -> str | None:
    """'Don't show OS', 'hide Saturdays', 'delete Physics class', 'show all again'.

    Hiding only affects YOUR views (chat, brief, My classes) — the whole-class
    view and other students are untouched. Deleting removes rows for real."""
    from backend.app.api.deps import get_user_context
    low = text.lower()
    uctx = get_user_context(db, student)
    hidden_subs = list(uctx.hidden_subjects)
    hidden_days = list(uctx.hidden_days)

    if re.search(r"\b(what|which|show|list).{0,25}(hidden|muted|hiding|hide)\b", low):
        bits = []
        if hidden_subs:
            bits.append("subjects: " + ", ".join(hidden_subs))
        if hidden_days:
            bits.append("days: " + ", ".join(DAY_NAMES[d] + "s" for d in hidden_days))
        return ("You're hiding " + "; ".join(bits) + ". Say 'show everything again' to undo."
                if bits else "You're not hiding anything right now. Say 'hide OS' or 'hide Saturdays' to change that.")

    if re.search(r"\b(show|unhide|unmute)\s+all\b", low) or "show everything" in low:
        set_pref(db, student.id, "hidden_subjects", [])
        set_pref(db, student.id, "hidden_days", [])
        return "Done — everything is visible again (your timetable rows are untouched)."

    delete_match = re.search(
        r"\b(delete|remove)\s+(?:the\s+)?(.+?)\s+(class|classes|lecture|subject)\b", low)
    if delete_match or ("delete" in low and "timetable" in low):
        target = (delete_match.group(2).strip() if delete_match else "")
        subj = _find_subject(low, subjects)
        if not subj and target:
            return (f"I couldn't find '{target}' in your timetable, so I deleted nothing. "
                    f"Your subjects: {', '.join(subjects) if subjects else 'none yet'}.")
        if not subj:
            return "Tell me which class to delete, e.g. 'delete Physics class'."
        removed = 0
        for entry in db.query(models.TimetableEntry).filter(
                models.TimetableEntry.student_id == student.id).all():
            if entry.subject.strip().lower() == subj.lower():
                db.delete(entry)
                removed += 1
        db.commit()
        return (f"Deleted {removed} '{subj}' row{'s' if removed != 1 else ''} from your timetable."
                if removed else f"No '{subj}' rows found — nothing deleted.")

    day = _find_day(low)
    subj = _find_subject(low, subjects)
    wants_hide = bool(re.search(r"\b(hide|mute|skip|don'?t show|stop showing|remove from view)\b", low))
    wants_show = bool(re.search(r"\b(unhide|unmute|show)\b", low)) and not wants_hide

    raw_match = re.search(
        r"(?:hide|mute|skip|don'?t show|stop showing)\s+(?:the\s+)?([a-z][a-z .&]{1,40})", low)
    if wants_hide and (day is not None or subj or raw_match):
        if day is not None and re.search(r"\b(day|whole day|anything|everything|all)\b", low):
            if day not in hidden_days:
                hidden_days.append(day)
            set_pref(db, student.id, "hidden_days", sorted(hidden_days))
            return f"Hidden {DAY_NAMES[day]}s from your views. Say 'show Saturdays again' anytime to undo."
        raw_name = raw_match.group(1).strip().lower() if raw_match else ""
        stop_words = {"me", "my", "it", "that", "this", "them", "us",
                      "please", "anything", "everything", "more", "emails",
                      "mail", "notifications", "messages"}
        if not subj and (not raw_name or any(w in stop_words for w in raw_name.split())):
            return None  # not a timetable request — let normal handling continue
        shown = subj or raw_name.title()
        if shown.lower() not in [s.lower() for s in hidden_subs]:
            hidden_subs.append(shown)
        set_pref(db, student.id, "hidden_subjects", hidden_subs)
        return (f"Hidden '{shown}' from your views (chat, brief, My classes). "
                "The rows still exist — say 'show it again' to undo, or 'delete it' to remove for real.")

    if wants_show and (day is not None or subj):
        if day is not None:
            hidden_days = [d for d in hidden_days if d != day]
            set_pref(db, student.id, "hidden_days", hidden_days)
            return f"{DAY_NAMES[day]}s are visible again."
        if subj:
            hidden_subs = [s for s in hidden_subs if s.lower() != subj.lower()]
            set_pref(db, student.id, "hidden_subjects", hidden_subs)
            return f"'{subj}' is visible again."
    return None


def handle_turn(db: Session, student: models.Student, text: str,
                channel: str = "caspian", now: datetime | None = None) -> str:
    now = now or utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if not onboarding.is_done(student):
        return onboarding.advance(db, student, text)

    c = make_ctx(db=db, student=student, now=now)
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
    if re.search(r"\b(my|list|show)\b.{0,15}\breminders?\b", low) and reminder is None:
        rems = tools.list_reminders(c)
        sections.append("Reminders: " + ("; ".join(
            f"{r['text']} (at {r['at']})" for r in rems) if rems else "none pending."))
    if ("add" in low or "create" in low) and any(w in low for w in ["task", "todo"]):
        title = re.sub(r"(?i)(add|create)\s+(a\s+)?(task|todo)\s*:?", "", text).strip() or text.strip()
        created = tools.create_task(c, title)
        sections.append(f"Task #{created['id']} created: {created['title']}.")

    visibility_reply = _handle_visibility(db, student, text, _known_subjects(db, student.id))
    if visibility_reply is not None:
        return visibility_reply

    if wants["plan"] or not any(wants.values()):
        plan = tools.generate_daily_plan(c)
        focus = tools.get_focus_now(c)
        compact = (channel != "web")  # Telegram/email: answer asked, not everything
        sections.append(f"Today ({DAY_NAMES[now.weekday()]}): {_fmt_classes(plan['today'])}.")
        sections.append(f"Next class: {plan['next_class']['subject']} "
                        f"{plan['next_class']['start']} Room {plan['next_class']['room'] or '—'}"
                        if plan["next_class"] else "Next class: none scheduled.")
        dl = plan["deadlines"]
        if dl:
            ranked_lines = []
            for d in dl[:3 if compact else 5]:
                _, label = tools.urgency_score(d, now)
                ranked_lines.append(f"{d['title']} (due {d['due']}) [{label}]")
            sections.append("Deadlines (ranked): " + "; ".join(ranked_lines) + ".")
        else:
            sections.append("Deadlines: none open.")
        ex = plan["exams"][:2 if compact else 3]
        sections.append("Exams: " + ("; ".join(
            f"{e['subject']} at {e['at']}" for e in ex) if ex else "none scheduled."))
        if not compact:
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
    if channel == "web":
        uctx = get_user_context(db, student)
        guide = [f"View: {uctx.batch_label}.", GUIDE_POINTER]
        if uctx.hidden_subjects or uctx.hidden_days:
            guide.append(f"{len(uctx.hidden_subjects)} subject(s) + {len(uctx.hidden_days)} day(s) "
                         "hidden by student and excluded above (mention only if asked).")
        context += "\n" + "\n".join(guide)
    return get_llm().complete(SYSTEM_BASE, text, context=context)
