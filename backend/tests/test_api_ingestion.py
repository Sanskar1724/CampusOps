"""API + PDF ingestion tests (isolated DB, TestClient)."""

from fastapi.testclient import TestClient

from backend.app.ingestion import pdf_source
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)

def _build_pdf(payload_text: bytes) -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
         b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"),
        b"<< /Length %d >>\nstream\n" % len(payload_text) + payload_text + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref_at))
    return out


MINIMAL_PDF = _build_pdf(
    b"BT /F1 12 Tf 72 720 Td (DBMS mid-semester exam Monday 10am Room 405.) Tj ET")


def register(email="api@college.edu", prn="API1"):
    resp = client.post("/api/auth/register", json={
        "full_name": "Api User", "prn": prn, "department": "CE", "division": "A",
        "batch": "B1", "roll_number": "7", "semester": "5", "course": "B.Tech",
        "college_email": email, "password": "secret123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_register_login_and_profile(db_session):
    headers = register()
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    bad = client.post("/api/auth/login",
                      json={"college_email": "api@college.edu", "password": "wrong"})
    assert bad.status_code == 401


def test_timetable_crud_and_chat(db_session):
    headers = register("tt@college.edu", "TT1")
    entry = {"day": 2, "subject": "DBMS", "start_time": "09:00",
             "end_time": "10:00", "room": "301"}
    assert client.post("/api/timetable/", json=entry, headers=headers).status_code == 200
    assert len(client.get("/api/timetable/", headers=headers).json()) == 1
    chat = client.post("/api/chat/", json={"text": "What is my next class?"},
                       headers=headers)
    assert chat.status_code == 200 and "DBMS" in chat.json()["reply"]


def test_deadline_task_flow(db_session):
    headers = register("plan@college.edu", "PL1")
    assert client.post("/api/planner/deadlines",
                       json={"title": "OS lab record", "due_at": "2026-09-12T17:00:00Z"},
                       headers=headers).status_code == 200
    assert client.post("/api/planner/tasks", json={"title": "Revise indexing"},
                       headers=headers).status_code == 200
    assert len(client.get("/api/planner/deadlines", headers=headers).json()) == 1


def test_pdf_upload_and_search(db_session):
    headers = register("doc@college.edu", "DOC1")
    client.post("/api/timetable/",
                json={"day": 0, "subject": "DBMS", "start_time": "09:00",
                      "end_time": "10:00", "room": "301"},
                headers=headers)
    resp = client.post("/api/documents/upload",
                       files={"file": ("calendar.pdf", MINIMAL_PDF, "application/pdf")},
                       headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["facts"].get("subject") == "DBMS"
    hits = client.get("/api/documents/search", params={"q": "DBMS exam"},
                      headers=headers).json()
    assert hits and "DBMS" in hits[0]["text"]
    bad = client.post("/api/documents/upload",
                      files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
                      headers=headers)
    assert bad.status_code == 400


def test_cross_student_access_blocked(db_session):
    alice = register("alice@college.edu", "AL1")
    bob = register("bob@college.edu", "BO1")
    entry_id = client.post(
        "/api/timetable/",
        json={"day": 0, "subject": "Secret", "start_time": "09:00", "end_time": "10:00"},
        headers=alice).json()["id"]
    assert client.delete(f"/api/timetable/{entry_id}", headers=bob).status_code == 404
    assert client.get("/api/timetable/", headers=bob).json() == []


def test_pdf_text_extraction_unit():
    text = pdf_source.extract_text("a.pdf", "application/pdf", MINIMAL_PDF)
    assert "DBMS" in text
