"""Demo seed: fictional student + timetable + emails + deadlines + document.
All rows are flagged demo (is_demo / source labels). Safe to re-run: it
skips when the demo student already exists."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.app import models
from backend.app.db import SessionLocal, init_db
from backend.app.ingestion import RawItem, email_source, timetable_source
from backend.app.llm import safe_json_loads
from backend.app.memory import add_chunk, save_memory
from backend.app.security import hash_password
from backend.app.services import detect_schedule_change

DEMO_PRN = "DEMO2026001"
DEMO_EMAIL = "demo.student@example.com"


def seed() -> int:
    from sqlalchemy import select  # noqa: E402
    init_db()
    db = SessionLocal()
    try:
        if db.scalar(select(models.Student).where(models.Student.prn == DEMO_PRN)):
            print("demo seed: already present, skipping")
            return 0
        now = datetime.now(timezone.utc)
        student = models.Student(
            full_name="Aarav Sharma", prn=DEMO_PRN, department="Computer Engineering",
            division="A", batch="B1", roll_number="21", semester="5", course="B.Tech",
            college_email=DEMO_EMAIL, password_hash=hash_password("demo1234"),
            onboarding_status="done", onboarding_step="done", is_demo=True)
        db.add(student)
        db.commit()
        db.refresh(student)

        timetable_source.replace_timetable(db, student.id, [
            {"day": "Monday", "subject": "DBMS", "start_time": "09:00", "end_time": "10:00",
             "room": "301", "faculty": "Prof. Iyer", "division": "A", "batch": "B1"},
            {"day": "Monday", "subject": "OS", "start_time": "11:00", "end_time": "12:00",
             "room": "302", "faculty": "Prof. Khan", "division": "A", "batch": "B1"},
            {"day": "Tuesday", "subject": "DBMS", "start_time": "10:00", "end_time": "11:00",
             "room": "301", "faculty": "Prof. Iyer", "division": "A", "batch": "B1"},
            {"day": "Tuesday", "subject": "Computer Networks", "start_time": "14:00",
             "end_time": "15:00", "room": "405", "faculty": "Prof. Rao", "division": "A", "batch": "B1"},
            {"day": "Wednesday", "subject": "OS", "start_time": "09:00", "end_time": "10:00",
             "room": "302", "faculty": "Prof. Khan", "division": "A", "batch": "B1"},
        ], source="seed")

        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        mails = [
            RawItem(external_id="seed:1", title="DBMS lecture moved to Room 405",
                    sender="dept@college.edu",
                    body=("Dear students, tomorrow's DBMS lecture has moved from Room 301 "
                          "to Room 405. — Dept office"),
                    received_at=now),
            RawItem(external_id="seed:2", title="CN assignment 4 due tomorrow",
                    sender="rao@college.edu",
                    body=("Computer Networks assignment 4 (TCP vs UDP comparison) is due "
                          f"tomorrow ({tomorrow}) by 5pm. Submit on the portal."),
                    received_at=now),
            RawItem(external_id="seed:3", title="Mid-semester exam schedule published",
                    sender="examcell@college.edu",
                    body=("The mid-semester DBMS exam is scheduled for next Monday at 10am "
                          "in the main hall. Hall tickets are mandatory."),
                    received_at=now),
            RawItem(external_id="seed:4", title="Weekend hackathon (optional)",
                    sender="clubs@college.edu",
                    body="Coding club hackathon this weekend. Open to all — good for your resume!",
                    received_at=now),
        ]
        for item in mails:
            ext = email_source.ingest_raw_email(db, student.id, item)
            detect_schedule_change(db, student.id, safe_json_loads(ext.facts_json, {}),
                                   f"email:{ext.email_id}")

        doc = models.Document(student_id=student.id, filename="academic-calendar-demo.pdf",
                              mime="application/pdf", size_bytes=1024,
                              facts_json='{"kind": "announcement"}', is_demo=True)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        add_chunk(db, doc, 0, ("Demo academic calendar: DBMS mid-semester exam next Monday 10am. "
                               "CN assignment 4 due tomorrow 5pm. Diwali break starts in three weeks."))

        save_memory(db, student.id, "preference", "reminder_style",
                    "Brief morning reminders only, no spam.", source="seed")
        save_memory(db, student.id, "project", "dbms_mini",
                    "Library management mini-project in DBMS, due end of month.", source="seed")
        print(f"demo seed: student {DEMO_PRN} ready (password: demo1234)")
        return student.id
    finally:
        db.close()


if __name__ == "__main__":
    seed()
