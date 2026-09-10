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
DONE_FMT = ("Thanks {name}! Your profile is saved. Ask me anything — "
            "try 'What should I focus on today?'")


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


def advance(db: Session, student: models.Student, text: str) -> str:
    step = student.onboarding_step
    value = text.strip()
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
