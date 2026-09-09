"""Timetable ingestion: CSV/JSON upload or manual rows. Entries are scoped by
division/batch so the agent only serves what applies to the student."""

from __future__ import annotations

import csv
import io
import json

from sqlalchemy.orm import Session

from backend.app import models

DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6}


def _day(value: str) -> int:
    value = value.strip().lower()
    if value.isdigit() and 0 <= int(value) <= 6:
        return int(value)
    if value in DAYS:
        return DAYS[value]
    raise ValueError(f"Unknown day: {value!r}")


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
