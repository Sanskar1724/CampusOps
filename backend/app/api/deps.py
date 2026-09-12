"""User-orientation router key. Every user-facing route builds its view of the
world through `get_user_context()` instead of raw rows: profile + batch,
hidden timetable rules, and notification preferences travel together, so chat,
timetable, briefs, and notifications all agree on what THIS student sees."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models

PREF_DEFAULTS: dict[str, object] = {
    "notify_brief": True,
    "notify_deadline": True,
    "notify_reminder": True,
    "notify_change": True,
    "notify_channel": "auto",  # auto | gateway | telegram
    "quiet_start": None,  # hour 0-23, local-ish (server time)
    "quiet_end": None,
    "hidden_subjects": [],
    "hidden_days": [],  # 0=Monday..6=Sunday
}


def get_prefs(db: Session, student_id: int) -> dict:
    prefs = dict(PREF_DEFAULTS)
    rows = db.scalars(select(models.StudentPreference).where(
        models.StudentPreference.student_id == student_id))
    for row in rows:
        try:
            prefs[row.key] = json.loads(row.value)
        except (ValueError, TypeError):
            prefs[row.key] = row.value
    return prefs


def set_pref(db: Session, student_id: int, key: str, value: object) -> None:
    row = db.scalar(select(models.StudentPreference).where(
        models.StudentPreference.student_id == student_id,
        models.StudentPreference.key == key))
    if row is None:
        row = models.StudentPreference(student_id=student_id, key=key)
        db.add(row)
    row.value = json.dumps(value)
    db.commit()


@dataclass
class UserContext:
    student: models.Student
    prefs: dict = field(default_factory=dict)

    @property
    def hidden_subjects(self) -> list[str]:
        return [str(s) for s in (self.prefs.get("hidden_subjects") or [])]

    @property
    def hidden_days(self) -> list[int]:
        return [int(d) for d in (self.prefs.get("hidden_days") or [])]

    @property
    def batch_label(self) -> str:
        s = self.student
        parts = [p for p in (s.division, s.batch) if p]
        return f"Div {'-'.join(parts)}" if parts else "whole class"

    def is_hidden(self, subject: str, day: int) -> bool:
        if day in self.hidden_days:
            return True
        slow = (subject or "").strip().lower()
        return any(slow == h.strip().lower() for h in self.hidden_subjects if h)


def get_user_context(db: Session, student: models.Student) -> UserContext:
    return UserContext(student=student, prefs=get_prefs(db, student.id))


KIND_TOGGLE = {
    "brief": "notify_brief",
    "deadline": "notify_deadline",
    "reminder": "notify_reminder",
    "change": "notify_change",
    "announcement": "notify_change",
}


def kind_allowed(prefs: dict, kind: str) -> bool:
    toggle = KIND_TOGGLE.get(kind)
    if toggle is None:
        return True
    return bool(prefs.get(toggle, True))


def in_quiet_hours(prefs: dict, now) -> bool:
    """Quiet window in server-local hours; wraps midnight (22→7)."""
    try:
        start = prefs.get("quiet_start")
        end = prefs.get("quiet_end")
        if start is None or end is None:
            return False
        hour = now.hour
        start, end = int(start), int(end)
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end
    except (ValueError, TypeError, AttributeError):
        return False
