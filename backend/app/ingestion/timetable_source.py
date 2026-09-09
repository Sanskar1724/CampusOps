"""Timetable ingestion: CSV/JSON upload, PDF text scan, or manual rows. Entries
are scoped by division/batch so the agent only serves what applies."""

from __future__ import annotations

import csv
import io
import json
import re

from sqlalchemy.orm import Session

from backend.app import models

DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6}
DAY_ABBR = {"mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3,
            "thurs": 3, "fri": 4, "sat": 5, "sun": 6}


def _day(value: str) -> int:
    value = value.strip().lower()
    if value.isdigit() and 0 <= int(value) <= 6:
        return int(value)
    if value in DAYS:
        return DAYS[value]
    if value in DAY_ABBR:
        return DAY_ABBR[value]
    raise ValueError(
        f"Unknown day: {value!r} (use Monday..Sunday, Mon..Sun, or 0..6).")


def _valid_time(value: str) -> str:
    parts = value.strip().split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Bad time: {value!r} (use HH:MM)")
    return f"{int(parts[0]):02d}:{int(parts[1]):02d}"


def replace_timetable(db: Session, student_id: int, rows: list[dict], source: str) -> int:
    parsed = []
    for row in rows:
        parsed.append(models.TimetableEntry(
            student_id=student_id, day=_day(str(row["day"])),
            subject=str(row["subject"]).strip(),
            start_time=_valid_time(str(row["start_time"])),
            end_time=_valid_time(str(row["end_time"])),
            room=str(row.get("room", "")), faculty=str(row.get("faculty", "")),
            division=str(row.get("division", "")), batch=str(row.get("batch", "")),
            source=source))
    db.query(models.TimetableEntry).filter(
        models.TimetableEntry.student_id == student_id).delete()
    db.add_all(parsed)
    db.commit()
    return len(parsed)


def parse_upload(filename: str, data: bytes) -> list[dict]:
    name = filename.lower()
    if name.endswith(".json"):
        rows = json.loads(data.decode("utf-8"))
        if not isinstance(rows, list):
            raise ValueError("JSON timetable must be a list of rows.")
        return rows
    if name.endswith(".csv"):
        return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
    raise ValueError("Upload .csv or .json (columns: day, subject, start_time, end_time, room, faculty).")


_DAY_ANY = re.compile(
    r"\b(mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|"
    r"fri(?:day)?|sat(?:urday)?|sun(?:day)?)\b", re.I)
_TIME_RANGE = re.compile(
    r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:-|–|to)\s*"
    r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)
_NOISE = re.compile(r"\b(room|lab|hall|faculty|prof\.?|div|batch)\b[\s:]*", re.I)


def _to_24(hour: int, minute: int, meridiem: str | None, other: str | None) -> str:
    mer = (meridiem or other or "").lower()
    if mer == "pm" and hour < 12:
        hour += 12
    if mer == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def extract_timetable_from_text(text: str) -> list[dict]:
    """Best-effort row detection for pasted/PDF timetable text. Each row needs
    a weekday, a time range, and a subject; room/faculty picked up when present.
    Splits on weekday boundaries (not newlines) because PDF extraction often
    merges lines."""
    rows = []
    flat = re.sub(r"\s+", " ", text)
    day_spans = list(_DAY_ANY.finditer(flat))
    chunks = []
    if day_spans:
        for i, match in enumerate(day_spans):
            end = day_spans[i + 1].start() if i + 1 < len(day_spans) else len(flat)
            chunks.append((match.group(1), flat[match.start():end]))
    else:
        chunks = []
    if not chunks:  # fall back to line scan for unusual layouts
        chunks = [(m.group(1), line) for line in text.splitlines()
                  for m in [_DAY_ANY.search(line)] if m and _TIME_RANGE.search(line)]
    for day_name, chunk in chunks:
        time_match = _TIME_RANGE.search(chunk)
        if not time_match:
            continue
        start = _to_24(int(time_match.group(1)), int(time_match.group(2) or 0),
                       time_match.group(3), time_match.group(6))
        end = _to_24(int(time_match.group(4)), int(time_match.group(5) or 0),
                     time_match.group(6), time_match.group(3))
        rest = _DAY_ANY.sub(" ", chunk)
        rest = _TIME_RANGE.sub(" ", rest)
        room = ""
        room_match = re.search(
            r"\b(?:[Rr]oom|[Ll]ab|LH|LT|[Hh]all)\s*[-:]?\s*([\w-]+)", rest)
        if room_match:
            room = room_match.group(1)
            rest = rest.replace(room_match.group(0), " ")
        subject = _NOISE.sub(" ", rest)
        subject = re.sub(r"[-–:;|,()]+", " ", subject)
        subject = re.sub(r"\s+", " ", subject).strip()
        if len(subject) < 2 or subject.lower() in ("am", "pm"):
            continue
        rows.append({"day": day_name, "subject": subject[:120],
                     "start_time": start, "end_time": end, "room": room})
    if not rows:
        raise ValueError(
            "No timetable rows found. I need lines with a weekday, a time range "
            "(e.g. 09:00-10:00), and a subject — paste that text or upload CSV/JSON.")
    return rows
