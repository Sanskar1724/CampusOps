"""All resource routers. Every query is scoped to the JWT student —
no endpoint ever accepts another student's id."""

from __future__ import annotations

import json
import os
from datetime import timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models, schemas, security
from backend.app.agents import onboarding
from backend.app.agents.core import handle_turn
from backend.app.db import get_db
from backend.app.ingestion import email_source, pdf_source, timetable_source
from backend.app.llm import safe_json_loads
from backend.app.memory import get_memories, save_memory, semantic_search
from backend.app.models import utcnow

Me = security.get_current_student


def _aware(value):
    """Treat naive datetimes as UTC so SQLite/Postgres comparisons stay valid."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# ---------- student / onboarding / memory ----------

student_router = APIRouter(prefix="/api/student", tags=["student"])


@student_router.get("/profile", response_model=schemas.StudentOut)
def profile(student: models.Student = Depends(Me)):
    return student


@student_router.patch("/profile", response_model=schemas.StudentOut)
def update_profile(payload: schemas.ProfileUpdate, db: Session = Depends(get_db),
                   student: models.Student = Depends(Me)):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    student.updated_at = utcnow()
    db.commit()
    db.refresh(student)
    return student


@student_router.post("/onboarding")
def onboarding_step(payload: schemas.OnboardingIn, db: Session = Depends(get_db),
                    student: models.Student = Depends(Me)):
    if onboarding.is_done(student):
        return {"reply": onboarding.WELCOME_BACK, "done": True}
    return {"reply": onboarding.advance(db, student, payload.text),
            "done": onboarding.is_done(student)}


@student_router.get("/memories")
def memories(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    return [{"id": m.id, "type": m.mem_type, "key": m.key, "value": m.value,
             "source": m.source, "confidence": m.confidence}
            for m in get_memories(db, student.id)]


@student_router.post("/memories")
def add_memory(payload: schemas.MemoryIn, db: Session = Depends(get_db),
               student: models.Student = Depends(Me)):
    mem = save_memory(db, student.id, payload.mem_type, payload.key,
                      payload.value, source="web", confidence=payload.confidence)
    return {"id": mem.id}


# ---------- timetable ----------

tt_router = APIRouter(prefix="/api/timetable", tags=["timetable"])


@tt_router.get("/")
def list_tt(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.TimetableEntry).where(
        models.TimetableEntry.student_id == student.id)
        .order_by(models.TimetableEntry.day, models.TimetableEntry.start_time)))
    return [schemas.TimetableOut.model_validate(r).model_dump() for r in rows]


@tt_router.post("/")
def add_tt(payload: schemas.TimetableIn, db: Session = Depends(get_db),
           student: models.Student = Depends(Me)):
    entry = models.TimetableEntry(student_id=student.id, **payload.model_dump())
    db.add(entry)
    db.commit()
    return {"id": entry.id}


@tt_router.put("/{entry_id}")
def edit_tt(entry_id: int, payload: schemas.TimetableIn, db: Session = Depends(get_db),
            student: models.Student = Depends(Me)):
    entry = db.get(models.TimetableEntry, entry_id)
    if not entry or entry.student_id != student.id:
        raise HTTPException(404, "Not found")
    for field, value in payload.model_dump().items():
        setattr(entry, field, value)
    db.commit()
    return {"id": entry.id}


@tt_router.delete("/{entry_id}")
def delete_tt(entry_id: int, db: Session = Depends(get_db),
              student: models.Student = Depends(Me)):
    entry = db.get(models.TimetableEntry, entry_id)
    if not entry or entry.student_id != student.id:
        raise HTTPException(404, "Not found")
    db.delete(entry)
    db.commit()
    return {"deleted": entry_id}


@tt_router.post("/upload")
async def upload_tt(file: UploadFile = File(...), db: Session = Depends(get_db),
                    student: models.Student = Depends(Me)):
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(400, "Timetable file too large (2 MB max).")
    try:
        rows = timetable_source.parse_upload(file.filename or "timetable.csv", data)
        count = timetable_source.replace_timetable(db, student.id, rows, source="upload")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"entries": count}


@tt_router.post("/from-document")
async def timetable_from_document(file: UploadFile = File(...),
                                  db: Session = Depends(get_db),
                                  student: models.Student = Depends(Me)):
    """Scan a PDF (or photo, when OCR is installed) and adopt detected rows."""
    from backend.app.ingestion import pdf_source  # noqa: E402
    data = await file.read()
    mime = file.content_type or ""
    if mime == "application/pdf" and len(data) > pdf_source.MAX_PDF_BYTES:
        raise HTTPException(400, "File exceeds the 10 MB limit.")
    if mime in pdf_source.IMAGE_MIME and len(data) > pdf_source.MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image exceeds the 5 MB limit.")
    if mime not in {pdf_source.PDF_MIME} | pdf_source.IMAGE_MIME:
        raise HTTPException(400, "Upload a PDF timetable (photos work once an OCR engine is installed).")
    try:
        text = pdf_source.extract_text(file.filename or "timetable.pdf", mime, data)
        rows = timetable_source.extract_timetable_from_text(text)
        count = timetable_source.replace_timetable(db, student.id, rows, source="pdf-scan")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"entries": count, "rows": rows}


# ---------- email intelligence ----------

email_router = APIRouter(prefix="/api/email", tags=["email"])


@email_router.get("/")
def list_emails(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.Email).where(
        models.Email.student_id == student.id)
        .order_by(models.Email.received_at.desc()).limit(50)))
    return [{"id": e.id, "sender": e.sender, "subject": e.subject,
             "body": e.body[:1000], "received_at": e.received_at} for e in rows]


@email_router.get("/important")
def important(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.EmailExtraction).where(
        models.EmailExtraction.student_id == student.id,
        models.EmailExtraction.status == "relevant")
        .order_by(models.EmailExtraction.created_at.desc()).limit(30)))
    out = []
    for x in rows:
        email = db.get(models.Email, x.email_id)
        out.append({"kind": x.kind, "priority": x.priority,
                    "facts": safe_json_loads(x.facts_json, {}),
                    "subject": email.subject if email else "",
                    "confidence": x.confidence})
    return out


def _gmail_access_token(db: Session, student: models.Student) -> str:
    integ = db.scalar(select(models.Integration).where(
        models.Integration.student_id == student.id,
        models.Integration.provider == "gmail"))
    if not integ or integ.status != "connected":
        raise HTTPException(409, "Gmail not connected — see /api/integrations/gmail/auth-url")
    return safe_json_loads(integ.meta_json, {}).get("access_token", "")


@email_router.post("/sync")
def sync_email(days: int = 7, limit: int = 20, db: Session = Depends(get_db),
               student: models.Student = Depends(Me)):
    """Pull college mail. Tune the window: /sync?days=30&limit=50 for a deep catch-up."""
    token = _gmail_access_token(db, student)
    try:
        items = email_source.GmailSource(token).fetch(db, student.id,
                                                      max_results=limit, days=days)
    except Exception as exc:
        raise HTTPException(502, f"Gmail fetch failed: {exc}")
    processed = [email_source.ingest_raw_email(db, student.id, item).id for item in items]
    from backend.app.services import detect_schedule_change  # noqa: E402
    for ext_id in processed:
        ext = db.get(models.EmailExtraction, ext_id)
        facts = safe_json_loads(ext.facts_json, {})
        detect_schedule_change(db, student.id, facts, f"email:{ext.email_id}")
    return {"processed": len(processed)}


# ---------- documents ----------

docs_router = APIRouter(prefix="/api/documents", tags=["documents"])


@docs_router.get("/")
def list_docs(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.Document).where(
        models.Document.student_id == student.id)
        .order_by(models.Document.created_at.desc())))
    return [{"id": d.id, "filename": d.filename, "size": d.size_bytes,
             "facts": safe_json_loads(d.facts_json, {})} for d in rows]


@docs_router.post("/upload")
async def upload_doc(file: UploadFile = File(...), db: Session = Depends(get_db),
                     student: models.Student = Depends(Me)):
    data = await file.read()
    try:
        doc = pdf_source.ingest_document(
            db, student.id, file.filename or "upload.pdf",
            file.content_type or "application/pdf", data)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    facts = safe_json_loads(doc.facts_json, {})
    return {"id": doc.id, "filename": doc.filename, "facts": facts,
            "extraction": facts.get("extraction", "text-layer"),
            "hint": ("Scanned document read with vision OCR." if facts.get("extraction") == "vision-ocr"
                     else None)}


@docs_router.get("/search")
def search_docs(q: str, db: Session = Depends(get_db),
                student: models.Student = Depends(Me)):
    return semantic_search(db, student.id, q)


@docs_router.delete("/{doc_id}")
def delete_doc(doc_id: int, db: Session = Depends(get_db),
               student: models.Student = Depends(Me)):
    doc = db.get(models.Document, doc_id)
    if not doc or doc.student_id != student.id:
        raise HTTPException(404, "Not found")
    db.delete(doc)
    db.commit()
    return {"deleted": doc_id}


# ---------- deadlines / exams / tasks / reminders ----------

plan_router = APIRouter(prefix="/api/planner", tags=["planner"])


@plan_router.get("/deadlines")
def list_deadlines(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.Deadline).where(
        models.Deadline.student_id == student.id).order_by(models.Deadline.due_at)))
    return [{"id": d.id, "title": d.title, "subject": d.subject, "due_at": d.due_at,
             "status": d.status, "priority": d.priority, "source": d.source} for d in rows]


@plan_router.post("/deadlines")
def add_deadline(payload: schemas.DeadlineIn, db: Session = Depends(get_db),
                 student: models.Student = Depends(Me)):
    data = payload.model_dump()
    data["due_at"] = _aware(data["due_at"])
    deadline = models.Deadline(student_id=student.id, **data)
    db.add(deadline)
    db.commit()
    return {"id": deadline.id}


@plan_router.post("/deadlines/{deadline_id}/done")
def done_deadline(deadline_id: int, db: Session = Depends(get_db),
                  student: models.Student = Depends(Me)):
    deadline = db.get(models.Deadline, deadline_id)
    if not deadline or deadline.student_id != student.id:
        raise HTTPException(404, "Not found")
    deadline.status = "done"
    db.commit()
    return {"id": deadline.id, "status": "done"}


@plan_router.get("/tasks")
def list_tasks(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.Task).where(
        models.Task.student_id == student.id).order_by(models.Task.created_at.desc())))
    return [{"id": t.id, "title": t.title, "detail": t.detail, "status": t.status,
             "due_at": t.due_at} for t in rows]


@plan_router.post("/tasks")
def add_task(payload: schemas.TaskIn, db: Session = Depends(get_db),
             student: models.Student = Depends(Me)):
    data = payload.model_dump()
    data["due_at"] = _aware(data["due_at"])
    task = models.Task(student_id=student.id, **data)
    db.add(task)
    db.commit()
    return {"id": task.id}


@plan_router.post("/tasks/{task_id}/done")
def done_task(task_id: int, db: Session = Depends(get_db),
              student: models.Student = Depends(Me)):
    task = db.get(models.Task, task_id)
    if not task or task.student_id != student.id:
        raise HTTPException(404, "Not found")
    task.status = "done"
    db.commit()
    return {"id": task.id, "status": "done"}


@plan_router.get("/reminders")
def list_reminders(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.Reminder).where(
        models.Reminder.student_id == student.id).order_by(models.Reminder.remind_at)))
    return [{"id": r.id, "text": r.text, "remind_at": r.remind_at, "status": r.status}
            for r in rows]


@plan_router.post("/reminders")
def add_reminder(payload: schemas.ReminderIn, db: Session = Depends(get_db),
                 student: models.Student = Depends(Me)):
    data = payload.model_dump()
    data["remind_at"] = _aware(data["remind_at"])
    reminder = models.Reminder(student_id=student.id, **data)
    db.add(reminder)
    db.commit()
    return {"id": reminder.id}


@plan_router.get("/exams")
def list_exams(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.Exam).where(
        models.Exam.student_id == student.id).order_by(models.Exam.exam_at)))
    return [{"id": e.id, "subject": e.subject, "title": e.title,
             "exam_at": e.exam_at, "room": e.room} for e in rows]


# ---------- notifications ----------

notif_router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@notif_router.get("/")
def list_notifs(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.Notification).where(
        models.Notification.student_id == student.id)
        .order_by(models.Notification.created_at.desc()).limit(50)))
    return [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body,
             "status": n.status, "created_at": n.created_at} for n in rows]


# ---------- chat (same Core Agent as Caspian) ----------

chat_router = APIRouter(prefix="/api/chat", tags=["chat"])


@chat_router.post("/", response_model=schemas.ChatOut)
def chat(payload: schemas.ChatIn, db: Session = Depends(get_db),
         student: models.Student = Depends(Me)):
    from backend.app.memory import get_or_create_conversation, log_message  # noqa: E402
    conv = get_or_create_conversation(db, channel="web", student_id=student.id)
    log_message(db, conv.id, "user", payload.text)
    reply = handle_turn(db, student, payload.text, channel="web")
    log_message(db, conv.id, "agent", reply)
    return {"reply": reply}


# ---------- integrations ----------

integr_router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@integr_router.get("/")
def list_integrations(db: Session = Depends(get_db),
                      student: models.Student = Depends(Me)):
    rows = list(db.scalars(select(models.Integration).where(
        models.Integration.student_id == student.id)))
    return [{"provider": i.provider, "status": i.status, "account": i.account_ref} for i in rows]


@integr_router.get("/gmail/auth-url")
def gmail_url(student: models.Student = Depends(Me)):
    client_id = os.environ.get("GMAIL_CLIENT_ID", "")
    redirect = os.environ.get("GMAIL_REDIRECT_URI", "http://localhost:8000/api/integrations/gmail/callback")
    if not client_id:
        raise HTTPException(409, "Gmail OAuth not configured on the server (GMAIL_CLIENT_ID).")
    state = security.make_oauth_state(student.id)
    return {"auth_url": email_source.gmail_auth_url(client_id, redirect, state=state)}


def _connect_gmail(db: Session, student: models.Student, code: str) -> None:
    try:
        tokens = email_source.gmail_exchange_code(
            os.environ.get("GMAIL_CLIENT_ID", ""), os.environ.get("GMAIL_CLIENT_SECRET", ""),
            code, os.environ.get("GMAIL_REDIRECT_URI",
                                 "http://localhost:8000/api/integrations/gmail/callback"))
    except Exception as exc:
        raise HTTPException(502, f"Gmail OAuth failed: {exc}")
    integ = db.scalar(select(models.Integration).where(
        models.Integration.student_id == student.id, models.Integration.provider == "gmail"))
    if not integ:
        integ = models.Integration(student_id=student.id, provider="gmail")
        db.add(integ)
    integ.status = "connected"
    integ.meta_json = json.dumps({"access_token": tokens.get("access_token", ""),
                                  "refresh_token": tokens.get("refresh_token", "")})
    integ.updated_at = utcnow()
    db.commit()


@integr_router.get("/gmail/callback")
def gmail_callback_get(code: str = "", state: str = "", db: Session = Depends(get_db)):
    """Google redirects here (GET) after the student clicks Allow. The signed
    `state` tells us which student approved, so no login is needed on this hop."""
    if not code:
        raise HTTPException(400, "Missing code from Google.")
    student = db.get(models.Student, security.read_oauth_state(state))
    if student is None:
        raise HTTPException(400, "Unknown student for this OAuth flow.")
    _connect_gmail(db, student, code)
    from fastapi.responses import HTMLResponse  # noqa: E402
    return HTMLResponse(
        "<body style='font-family:sans-serif;text-align:center;padding-top:15%'>"
        "<h2>Gmail connected ✓</h2>"
        "<p>You can close this tab and press Refresh in CampusOps.</p></body>")


@integr_router.post("/gmail/callback")
def gmail_callback(payload: schemas.GmailCallbackIn, db: Session = Depends(get_db),
                   student: models.Student = Depends(Me)):
    """Manual paste fallback (Settings → Finish button)."""
    _connect_gmail(db, student, payload.code)
    return {"status": "connected"}


@integr_router.delete("/gmail")
def gmail_disconnect(db: Session = Depends(get_db),
                     student: models.Student = Depends(Me)):
    integ = db.scalar(select(models.Integration).where(
        models.Integration.student_id == student.id, models.Integration.provider == "gmail"))
    if integ:
        integ.status = "disconnected"
        integ.meta_json = "{}"
        db.commit()
    return {"status": "disconnected"}
