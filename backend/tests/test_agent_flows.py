"""End-to-end behavior: onboarding → agent answers → isolation → jobs."""

from datetime import datetime, timedelta, timezone

from backend.app import models
from backend.app.agents.core import handle_turn
from backend.app.comms.handlers import get_or_create_student_for_sender
from backend.app.ingestion import RawItem, email_source
from backend.app.ingestion.extract import classify, extract_facts
from backend.app.ingestion.timetable_source import replace_timetable
from backend.app.jobs import build_daily_brief, run_all
from backend.app.llm import safe_json_loads
from backend.app.memory import save_memory, semantic_search
from backend.app.security import hash_password
from backend.app.services import detect_schedule_change

NOW = datetime(2026, 9, 9, 6, 0, tzinfo=timezone.utc)  # a Wednesday


def make_student(db_session, **over):
    data = {"full_name": "Test Student", "prn": "T1", "department": "CE",
            "division": "A", "batch": "B1", "roll_number": "1", "semester": "5",
            "course": "B.Tech", "college_email": "t1@college.edu",
            "password_hash": hash_password("secret123"),
            "onboarding_status": "done", "onboarding_step": "done"}
    data.update(over)
    student = models.Student(**data)
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


def seed_timetable(db_session, student):
    replace_timetable(db_session, student.id, [
        {"day": "Wednesday", "subject": "DBMS", "start_time": "09:00",
         "end_time": "10:00", "room": "301", "faculty": "Prof. Iyer"},
        {"day": "Thursday", "subject": "OS", "start_time": "11:00",
         "end_time": "12:00", "room": "302", "faculty": "Prof. Khan"},
    ], source="test")


def test_onboarding_conversation_completes(db_session):
    student = get_or_create_student_for_sender(db_session, "newbie@example.com")
    answers = ["Rahul Patil", "PRN123", "Computer Engineering", "A", "B1",
               "42", "5", "B.Tech", "rahul@college.edu"]
    replies = [handle_turn(db_session, student, a) for a in answers]
    assert "PRN" in replies[0]
    assert "saved" in replies[-1].lower() or "anything" in replies[-1].lower()
    db_session.refresh(student)
    assert student.onboarding_status == "done"
    assert student.full_name == "Rahul Patil"
    assert student.prn == "PRN123"


def test_onboarding_rejects_duplicate_prn(db_session):
    make_student(db_session, prn="DUP1", college_email="dup@college.edu")
    other = get_or_create_student_for_sender(db_session, "other@example.com")
    handle_turn(db_session, other, "Some Name")
    reply = handle_turn(db_session, other, "DUP1")
    assert "already registered" in reply


def test_agent_answers_from_timetable_and_deadlines(db_session):
    student = make_student(db_session)
    seed_timetable(db_session, student)
    db_session.add(models.Deadline(student_id=student.id, title="CN assignment 4",
                                   subject="Computer Networks",
                                   due_at=datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc)))
    db_session.commit()
    reply = handle_turn(db_session, student, "What should I focus on today?", now=NOW)
    assert "DBMS" in reply
    assert "cn assignment 4" in reply.lower()
    nxt = handle_turn(db_session, student, "What is my next class?", now=NOW)
    assert "DBMS" in nxt


def test_reminder_created_from_chat(db_session):
    student = make_student(db_session)
    reply = handle_turn(db_session, student, "Remind me about DBMS revision tomorrow at 9am", now=NOW)
    assert "reminder" in reply.lower() and "dbms" in reply.lower()
    assert db_session.query(models.Reminder).filter_by(student_id=student.id).count() == 1


def test_student_isolation(db_session):
    alice = make_student(db_session, prn="A1", college_email="a@college.edu")
    bob = make_student(db_session, prn="B1", college_email="b@college.edu")
    seed_timetable(db_session, alice)
    reply_bob = handle_turn(db_session, bob, "What do I have today?", now=NOW)
    assert "DBMS" not in reply_bob
    save_memory(db_session, alice.id, "fact", "nick", "Ally")
    assert "Ally" not in handle_turn(db_session, bob, "What do you remember about me?", now=NOW)


def test_email_pipeline_and_change_detection(db_session):
    student = make_student(db_session)
    seed_timetable(db_session, student)
    ext = email_source.ingest_raw_email(db_session, student.id, RawItem(
        external_id="t:1", title="DBMS moved to Room 405", sender="dept@college.edu",
        body="DBMS lecture tomorrow has moved from Room 301 to Room 405."))
    facts = safe_json_loads(ext.facts_json, {})
    assert facts["subject"] == "DBMS"
    assert facts["new_room"] == "405"
    note = detect_schedule_change(db_session, student.id, facts, "email:1")
    assert note is not None and "405" in note.body


def test_reingest_does_not_duplicate(db_session):
    student = make_student(db_session)
    seed_timetable(db_session, student)
    item = RawItem(external_id="dup:1", title="CN assignment due Friday",
                   sender="rao@college.edu",
                   body="Computer Networks assignment is due Friday.")
    first = email_source.ingest_raw_email(db_session, student.id, item)
    second = email_source.ingest_raw_email(db_session, student.id, item)
    assert first.id == second.id
    assert db_session.query(models.Email).filter_by(
        student_id=student.id, external_id="dup:1").count() == 1
    assert db_session.query(models.EmailExtraction).filter_by(
        email_id=first.email_id).count() == 1


def test_classifier_kinds():
    assert classify("Submit DBMS assignment by Friday")[0] == "assignment"
    assert classify("Mid-semester exam on Monday")[0] == "exam"
    assert classify("Placement drive: Infosys interviews")[0] == "placement"
    assert classify("ok")[0] == "irrelevant"
    facts = extract_facts("CN assignment due tomorrow", ["Computer Networks"])
    assert facts.get("due_date") is not None


def test_daily_brief_content(db_session):
    student = make_student(db_session)
    seed_timetable(db_session, student)
    title, body = build_daily_brief(db_session, student, NOW)
    assert "GOOD MORNING" in body and "DBMS" in body and "09:00" in body


def test_worker_sweep_sends_reminder_once(db_session):
    student = make_student(db_session)
    db_session.add(models.Reminder(student_id=student.id, text="Revise OS",
                                   remind_at=NOW - timedelta(minutes=5)))
    db_session.commit()
    first = run_all(db_session, NOW)
    second = run_all(db_session, NOW)
    assert first["reminders"] == 1
    assert second["reminders"] == 0  # no repeat spam
    assert db_session.query(models.Notification).filter_by(
        student_id=student.id, kind="reminder").count() == 1


def test_semantic_memory_search(db_session):
    student = make_student(db_session)
    doc = models.Document(student_id=student.id, filename="notes.pdf",
                          mime="application/pdf", size_bytes=10)
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    from backend.app.memory import add_chunk
    add_chunk(db_session, doc, 0, "DBMS normalization rules for the upcoming exam")
    add_chunk(db_session, doc, 1, "Cricket club meeting on Sunday evening")
    hits = semantic_search(db_session, student.id, "DBMS exam preparation")
    assert hits and hits[0]["text"].startswith("DBMS")
