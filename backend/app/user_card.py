"""User card: the student's portable markdown profile for the system prompt.

This is the "md file" idea made runtime-real: instead of a static document,
the card is rebuilt fresh every turn from live data (profile, batch-filtered
timetable, deadlines, exams, updates, memories, hidden rules), so the model
always reasons about THIS student — name, batch, classes, priorities — and
answers like a personal tutor, not a template. See docs/USER_CARD_SPEC.md
for the exact format contract."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend.app import models
from backend.app.agents.tools import (
    DAY_NAMES,
    Ctx,
    get_day_schedule,
    get_important_updates,
    get_upcoming_deadlines,
    get_upcoming_exams,
)
from backend.app.api.deps import get_user_context
from backend.app.memory import get_memories


def build_user_card_md(db: Session, student: models.Student, now: datetime) -> str:
    uctx = get_user_context(db, student)
    c = Ctx(db=db, student=student, now=now,
            hidden_subjects=uctx.hidden_subjects, hidden_days=uctx.hidden_days)
    lines = [
        f"# Student: {student.full_name or 'there'}",
        f"- Dept {student.department or '—'} · Div {student.division or '—'} · "
        f"Batch {student.batch or '—'} · Sem {student.semester or '—'} · "
        f"Roll {student.roll_number or '—'}",
        f"- View scope: {uctx.batch_label} (timetable below is already filtered to it)",
    ]
    today = get_day_schedule(c, now.weekday())
    lines.append("- Today ({}): {}".format(
        DAY_NAMES[now.weekday()],
        "; ".join(f"{x['subject']} {x['start']}-{x['end']} Room {x['room'] or '—'}"
                  for x in today) or "no classes"))
    dl = get_upcoming_deadlines(c, days=14)[:5]
    lines.append("- Deadlines: " + ("; ".join(
        f"{d['title']} (due {d['due']}, {d['priority']})" for d in dl) or "none open"))
    ex = get_upcoming_exams(c, days=30)[:3]
    lines.append("- Exams: " + ("; ".join(
        f"{e['subject']} at {e['at'] or 'TBA'}" for e in ex) or "none scheduled"))
    imp = get_important_updates(c, limit=3)
    lines.append("- Recent alerts: " + ("; ".join(
        f"{i['title']} [{i['priority']}]" for i in imp) or "nothing new"))
    mems = get_memories(db, student.id)[:8]
    lines.append("- Remember about them: " + ("; ".join(
        f"{m.key} = {m.value[:120]}" for m in mems) or "nothing stored yet"))
    if uctx.hidden_subjects or uctx.hidden_days:
        lines.append("- Hidden from their views: "
                     + ", ".join(uctx.hidden_subjects +
                                 [DAY_NAMES[d] + "s" for d in uctx.hidden_days]))
    lines.append("- Style: warm, specific, varied wording; use their first name "
                 "occasionally; never repeat a previous reply verbatim.")
    return "\n".join(lines)
