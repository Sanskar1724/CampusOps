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
        canon = _canonicalize(row)
        parsed.append(models.TimetableEntry(
            student_id=student_id, day=_day(str(canon["day"])),
            subject=str(canon["subject"]).strip(),
            start_time=_valid_time(str(canon["start_time"])),
            end_time=_valid_time(str(canon["end_time"])),
            room=str(canon.get("room", "")), faculty=str(canon.get("faculty", "")),
            division=str(canon.get("division", "")), batch=str(canon.get("batch", "")),
            source=source))
    db.query(models.TimetableEntry).filter(
        models.TimetableEntry.student_id == student_id).delete()
    db.add_all(parsed)
    db.commit()
    return len(parsed)


# --- Flexible header handling: real college CSVs never use our exact names. ---
_HEADER_ALIASES = {
    "day": {"day", "weekday", "days", "dayname", "day_name"},
    "subject": {"subject", "course", "sub", "class", "paper", "title",
                "subjectname", "subject_name", "course_name"},
    "start_time": {"start_time", "start", "from", "from_time", "starttime",
                   "time_from", "begins", "stime", "startat", "start_at"},
    "end_time": {"end_time", "end", "to", "to_time", "endtime",
                 "time_to", "ends", "etime", "endat", "end_at"},
    "time": {"time", "timing", "slot", "timerange", "time_range", "duration",
             "hours", "period"},
    "room": {"room", "venue", "lab", "hall", "classroom", "room_no", "roomno"},
    "faculty": {"faculty", "teacher", "prof", "professor", "lecturer",
                "instructor", "tutor", "faculty_name"},
    "division": {"division", "div", "section"},
    "batch": {"batch", "group"},
}

_CANONICAL_ORDER = ("day", "subject", "start_time", "end_time",
                    "room", "faculty", "division", "batch")


def _alias_of(header: str) -> str | None:
    key = re.sub(r"[^a-z]", "", header.strip().lower())
    for canon, variants in _HEADER_ALIASES.items():
        if key in {re.sub(r"[^a-z]", "", v) for v in variants}:
            return canon
    return None


def applies_to(entry_division: str, entry_batch: str,
               student_division: str, student_batch: str) -> bool:
    """One shared rule: blank entry fields mean 'everyone'; otherwise the
    entry must match the student's division/batch. Used by the agent tools,
    the timetable API filter, and the frontend's 'my classes' view."""
    ed, eb = (entry_division or "").strip(), (entry_batch or "").strip()
    sd, sb = (student_division or "").strip(), (student_batch or "").strip()
    if ed and sd and ed.lower() != sd.lower():
        return False
    if eb and sb and eb.lower() != sb.lower():
        return False
    return True


def _canonicalize(row: dict) -> dict:
    """Map any aliased row (CSV/JSON with natural headers) to canonical keys."""
    canon: dict = {}
    for raw_key, value in row.items():
        alias = _alias_of(str(raw_key))
        if alias and alias not in canon:
            canon[alias] = value
    # A combined "Time" column like "09:00-10:00" or "9am-10am".
    if "time" in canon and ("start_time" not in canon or "end_time" not in canon):
        m = _TIME_RANGE.search(str(canon["time"]))
        if m:
            canon.setdefault("start_time", _to_24(
                int(m.group(1)), int(m.group(2) or 0), m.group(3), m.group(6)))
            canon.setdefault("end_time", _to_24(
                int(m.group(4)), int(m.group(5) or 0), m.group(6), m.group(3)))
    missing = [k for k in ("day", "subject", "start_time", "end_time")
               if not str(canon.get(k, "")).strip()]
    if missing:
        raise ValueError(
            f"Row is missing {', '.join(missing)} (columns seen: "
            f"{', '.join(str(k) for k in row.keys()) or 'none'}). "
            "Use headers like: day, subject, start_time, end_time, room, faculty "
            "— 'Day/Subject/Start/End', 'Time' ranges, and 'Teacher/Room' all work.")
    return canon


def parse_upload(filename: str, data: bytes) -> list[dict]:
    name = filename.lower()
    if name.endswith(".json"):
        rows = json.loads(data.decode("utf-8-sig"))
        if not isinstance(rows, list):
            raise ValueError("JSON timetable must be a list of rows.")
    elif name.endswith(".csv"):
        text = data.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
    else:
        raise ValueError("Upload .csv or .json (columns: day, subject, start_time, end_time, room, faculty).")
    cleaned = [r for r in rows
               if any(str(v or "").strip() for v in r.values())]
    if not cleaned:
        raise ValueError("No data rows found in the file — is the first row a header?")
    return [_canonicalize(r) for r in cleaned]


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


# Batch-parallel cells: one slot lists every batch, e.g.
# "D1 CIS JSL — H305 D2 CN PGM — H306B D3 OS PVU — E421".
# D-markers are batch groups here (a D3 student only attends the D3 part).
_BATCH_MARK = re.compile(r"\b(D\d+|B\d+|WT\d+|LA\d+|MAD\d+)\b", re.I)
_BREAK_WORDS = re.compile(r"\b(short\s+break|lunch\s+break|break|recess)\b", re.I)
_ROOM_CODE = re.compile(r"[—–-]\s*([A-Z]{1,4}\d+[A-Z]*)")
_FACULTY_TOKEN = re.compile(r"^[A-Z]{2,4}$")
_COURSE_CODE = re.compile(r"^[A-Z/&]+[0-9]+[A-Z0-9/&]*$")
_ROMAN = {"I", "II", "III", "IV", "V", "VI", "VII"}
_LAB_WORDS = {"RL", "CL", "PL", "CNL"}


def _clean_subject(window: str) -> tuple[str, str, str, str, str]:
    """Split a batch segment into (subject, room, division, batch, faculty).

    Section tokens like 'Div A' / 'Batch B1' are captured into fields instead
    of polluting the subject, so the week can later be filtered per student.
    All-caps runs ('TY MDM TH', 'OS PVU') are kept whole — splitting faculty
    initials out of them mangles more than it helps."""
    room = ""
    code_match = _ROOM_CODE.search(window)
    if code_match:
        room = code_match.group(1)
        window = window.replace(code_match.group(0), " ")
    else:
        room_match = re.search(
            r"\b(?:[Rr]oom|[Ll]ab|LH|LT|[Hh]all)\s*[-:]?\s*([\w-]+)", window)
        if room_match:
            room = room_match.group(1)
            window = window.replace(room_match.group(0), " ")
    division, batch = "", ""
    div_match = re.search(r"\bdiv(?:ision)?[\s:.-]*([A-Z0-9]+)\b", window, flags=re.I)
    if div_match:
        division = div_match.group(1).upper()
        window = window.replace(div_match.group(0), " ")
    batch_match = re.search(r"\bbatch[\s:.-]*([A-Z0-9]+)\b", window, flags=re.I)
    if batch_match:
        batch = batch_match.group(1).upper()
        window = window.replace(batch_match.group(0), " ")
    # Faculty spelled out ("Prof Iyer").
    prof = re.search(r"\b(?:prof|dr|faculty)\.?\s+([A-Z][a-z]+)\b", window, flags=re.I)
    faculty = prof.group(1) if prof else ""
    window = re.sub(r"\b(?:prof|dr|faculty)\.?\s+[A-Z][a-z]+\b", " ", window, flags=re.I)
    window = _NOISE.sub(" ", window)
    window = re.sub(r"[-–:;|,()]+", " ", window)
    tokens = [t for t in re.sub(r"\s+", " ", window).strip().split(" ") if t]
    # PDF line-merge often duplicates the cell ("TY MDM TH TY MDM TH").
    if len(tokens) % 2 == 0 and len(tokens) >= 4 and tokens[:len(tokens) // 2] == tokens[len(tokens) // 2:]:
        tokens = tokens[:len(tokens) // 2]
    # Drop course codes glued in front ("CIS1 CIS" -> "CIS").
    while tokens and _COURSE_CODE.match(tokens[0]):
        tokens.pop(0)
    # Drop lab/section noise ("RL", "CL II", "CNL I").
    tokens = [t for t in tokens if t not in _LAB_WORDS and t not in _ROMAN]
    # Narrow rule: short code + one name ("WT Vaishali" -> WT + Vaishali).
    if (len(tokens) == 2 and len(tokens[0]) <= 4
            and re.fullmatch(r"[A-Z][a-z]+", tokens[1]) and not faculty):
        faculty, tokens = tokens[1], [tokens[0]]
    subject = " ".join(tokens).strip()
    return subject, room, division, batch, faculty


def _split_batches(window: str) -> list[tuple[str, str]]:
    """Split a time window into per-batch segments.

    Returns [(batch_marker_or_"", text)]. A meaningful shared prefix before
    the first marker (e.g. a common lecture) comes back as a ("", text) part;
    pure break-words prefix is dropped. Windows without markers come back
    whole (common to everyone)."""
    marks = list(_BATCH_MARK.finditer(window))
    if not marks:
        return [("", window)]
    parts = []
    prefix = window[:marks[0].start()].strip()
    if prefix and not _is_break_only(prefix):
        parts.append(("", prefix))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(window)
        parts.append((m.group(1).upper(), window[m.end():end]))
    if not any(seg.strip() for _, seg in parts):
        return [("", window)]
    return parts


def _is_break_only(text: str) -> str:
    """If the text is just a break label, return which kind, else ''."""
    cleaned = _BREAK_WORDS.sub(" ", text)
    cleaned = re.sub(r"[-–:;|,()]+", " ", cleaned)
    if not re.sub(r"\s+", "", cleaned):
        low = text.lower()
        return "Lunch Break" if "lunch" in low else "Short Break"
    return ""


def extract_timetable_from_text(text: str) -> list[dict]:
    """Best-effort row detection for pasted/PDF timetable text.

    Handles the layouts college PDFs actually use: several classes under one
    weekday header ("Monday 9-10 DBMS, 11-12 OS"), table rows with pipes, and
    day-header blocks where the day sits on its own line. Every time range in
    a day's span becomes its own row; the subject is read from the text
    surrounding that range (before or after it)."""
    rows = []
    flat = re.sub(r"\s+", " ", text)
    day_spans = list(_DAY_ANY.finditer(flat))
    segments: list[tuple[str, str]] = []
    if day_spans:
        for i, match in enumerate(day_spans):
            end = day_spans[i + 1].start() if i + 1 < len(day_spans) else len(flat)
            segments.append((match.group(1), flat[match.start():end]))
    if not segments:  # fall back to line scan for unusual layouts
        segments = [(m.group(1), line) for line in text.splitlines()
                    for m in [_DAY_ANY.search(line)] if m and _TIME_RANGE.search(line)]
    for day_name, chunk in segments:
        # Strip the leading weekday word so it can't leak into a subject.
        body = _DAY_ANY.sub(" ", chunk, count=1)
        times = list(_TIME_RANGE.finditer(body))
        for j, time_match in enumerate(times):
            start = _to_24(int(time_match.group(1)), int(time_match.group(2) or 0),
                           time_match.group(3), time_match.group(6))
            end = _to_24(int(time_match.group(4)), int(time_match.group(5) or 0),
                         time_match.group(6), time_match.group(3))
            win_start = times[j - 1].end() if j > 0 else 0
            win_end = times[j + 1].start() if j + 1 < len(times) else len(body)
            window = body[win_start:win_end]
            window = _DAY_ANY.sub(" ", window)
            window = _TIME_RANGE.sub(" ", window)
            # One slot may list every batch ("D1 … D2 … D3 …"): split it so a
            # D3 student only ever sees the D3 part.
            for marker, seg in _split_batches(window):
                seg = seg.strip()
                if not seg:
                    continue
                break_kind = _is_break_only(seg)
                if break_kind and not marker:
                    rows.append({"day": day_name, "subject": break_kind,
                                 "start_time": start, "end_time": end, "room": "",
                                 "division": "", "batch": "", "faculty": ""})
                    continue
                seg = _BREAK_WORDS.sub(" ", seg)
                subject, room, division, batch, faculty = _clean_subject(seg)
                if not marker and (len(subject) < 2 or subject.lower() in ("am", "pm")):
                    continue
                if re.fullmatch(r"[\d\s]+", subject or ""):
                    continue
                if marker and not subject:
                    continue
                rows.append({"day": day_name, "subject": (subject or break_kind or "Class")[:120],
                             "start_time": start, "end_time": end, "room": room,
                             "division": division, "batch": marker or batch,
                             "faculty": faculty})
    if not rows:
        raise ValueError(
            "No timetable rows found. I need lines with a weekday, a time range "
            "(e.g. 09:00-10:00), and a subject — paste that text or upload CSV/JSON.")
    if len(rows) > 80:
        raise ValueError(
            f"Found {len(rows)} rows, which looks like a misread (a week has ~50 "
            "classes max). Please upload the CSV export from your portal instead.")
    return rows
