"""Conversational onboarding. Shared by the Caspian flow and the web API:
both call `next_prompt` / `advance` — one state machine, two channels."""

from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.llm import safe_json_loads

STEPS: list[tuple[str, str]] = [
    ("full_name", "Welcome to CampusOps! What's your full name?"),
    ("prn", "What is your PRN (Permanent Registration Number)?"),
    ("department", "Which department are you in? (e.g. Computer Engineering)"),
    ("division", "Which division? (e.g. A)"),
    ("batch", "Which batch? (e.g. B1)"),
    ("roll_number", "What is your roll number?"),
    ("semester", "Which semester are you in? (e.g. 5)"),
    ("college_email", "Finally, what is your college email address?"),
]

WELCOME_BACK = "Welcome back to CampusOps! You're all set. Ask me anything — try 'What should I focus on today?'"
DONE_FMT = ("Thanks {name}! Your profile is saved. 🎉\n\n"
            "Quick tour: ask 'What should I focus on today?', "
            "'What is my next class?', or 'Did my timetable change?'. "
            "On Telegram, tap the buttons below any reply, or try /today /deadlines /help. "
            "Hide anything with 'hide OS' — unhide with 'show everything'.")

# Academic questions must never be swallowed as an onboarding answer
# (e.g. "What do I have today?" was saved as the division field).
ACADEMIC_QUESTION_RE = re.compile(
    r"\b(what|when|where|which|who|how|show|list|do i|is there|are there|"
    r"today|tomorrow|timetable|class|deadline|exam|reminder|task|brief|"
    r"focus|schedule|room|change|next|week|assignment|test|syllabus|"
    r"holiday|attendance|marks?|grade|fee|library)\b"
    r"|\?"
)


def looks_like_academic_question(text: str) -> bool:
    """True when `text` reads like a normal academic question/request.

    Long multi-word messages are questions, not single onboarding field
    values — route them to the normal agent instead of saving them as
    e.g. the student's division.
    """
    value = text.strip()
    if not value:
        return False
    if len(value.split()) >= 4:
        return True
    return bool(ACADEMIC_QUESTION_RE.search(value.lower()))


def _draft(student: models.Student) -> dict:
    return safe_json_loads(student.onboarding_draft, {})


def _save_draft(db: Session, student: models.Student, draft: dict) -> None:
    student.onboarding_draft = json.dumps(draft)
    db.commit()


def is_done(student: models.Student) -> bool:
    return student.onboarding_status == "done"


def next_prompt(student: models.Student) -> str:
    for step, question in STEPS:
        if step == student.onboarding_step:
            return question
    return STEPS[0][1]


def advance(db: Session, student: models.Student, text: str) -> str | None:
    step = student.onboarding_step
    value = text.strip()
    if step not in ("full_name", "prn", "college_email") and looks_like_academic_question(value):
        # Normal academic questions (e.g. "What do I have today?") are NOT
        # onboarding answers — signal the caller to handle them normally
        # instead of saving them as e.g. the student's division.
        return None
    draft = _draft(student)

    if step == "prn":
        if db.scalar(select(models.Student).where(
                models.Student.prn == value,
                models.Student.id != student.id)):
            return "That PRN is already registered. Please check and resend your PRN."
        setattr(student, "prn", value)
    elif step == "college_email":
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
            return "That doesn't look like an email address. Please resend your college email."
        taken = db.scalar(select(models.Student).where(
            models.Student.college_email == value, models.Student.id != student.id))
        if taken:
            return "That email is already registered. Please resend your college email."
        student.college_email = value
    elif step in dict(STEPS):
        setattr(student, step, value)
    draft[step] = value

    order = [s for s, _ in STEPS]
    idx = order.index(step) if step in order else 0
    if idx + 1 >= len(order):
        student.onboarding_status = "done"
        student.onboarding_step = "done"
        _save_draft(db, student, draft)
        db.commit()
        return DONE_FMT.format(name=student.full_name or "there")
    student.onboarding_step = order[idx + 1]
    _save_draft(db, student, draft)
    db.commit()
    return next_prompt(student)
