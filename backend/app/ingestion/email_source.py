"""Email pipeline: fetch (Gmail REST or dev/seed rows) → classify → extract →
relevance → memory. Passwords are never asked for or stored; Gmail uses
read-only OAuth and only token references live in `integrations`."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.ingestion import RawItem
from backend.app.ingestion.extract import classify, confidence_for, enrich_with_llm, extract_facts
from backend.app.models import utcnow


def student_subjects(db: Session, student_id: int) -> list[str]:
    rows = db.scalars(select(models.TimetableEntry.subject).where(
        models.TimetableEntry.student_id == student_id).distinct())
    return [r for r in rows if r]


def ingest_raw_email(db: Session, student_id: int, item: RawItem) -> models.EmailExtraction:
    existing = db.scalar(select(models.Email).where(
        models.Email.student_id == student_id,
        models.Email.external_id == item.external_id))
    if existing:
        prior = db.scalar(select(models.EmailExtraction).where(
            models.EmailExtraction.email_id == existing.id))
        if prior:
            return prior  # re-syncs must not duplicate facts/deadlines
        return process_email(db, existing)
    email = models.Email(student_id=student_id, external_id=item.external_id,
                         sender=item.sender, subject=item.title, body=item.body,
                         received_at=item.received_at or utcnow())
    db.add(email)
    db.commit()
    db.refresh(email)
    return process_email(db, email)


def process_email(db: Session, email: models.Email) -> models.EmailExtraction:
    subjects = student_subjects(db, email.student_id)
    text = f"{email.subject}\n{email.body}"
    kind, priority = classify(text)
    facts = enrich_with_llm(text, extract_facts(text, subjects))
    extraction = models.EmailExtraction(
        email_id=email.id, student_id=email.student_id, kind=kind, priority=priority,
        facts_json=json.dumps(facts), confidence=confidence_for(kind, facts))
    db.add(extraction)
    db.commit()
    db.refresh(extraction)
    apply_relevance(db, email, extraction, facts)
    return extraction


def apply_relevance(db: Session, email: models.Email, extraction: models.EmailExtraction, facts: dict) -> None:
    """Student relevance: does this item concern THIS student's subjects?"""
    if extraction.kind == "irrelevant":
        extraction.status = "ignored"
        db.commit()
        return
    relevant = True
    subject = facts.get("subject")
    if subject:
        relevant = subject in student_subjects(db, email.student_id)
    if not relevant:
        extraction.status = "not_relevant"
        db.commit()
        return
    extraction.status = "relevant"
    if extraction.kind in ("assignment", "deadline") and facts.get("due_date"):
        due = datetime.fromisoformat(facts["due_date"]).replace(tzinfo=timezone.utc)
        source_id = f"email:{email.id}"
        if not db.scalar(select(models.Deadline).where(
                models.Deadline.student_id == email.student_id,
                models.Deadline.source_id == source_id)):
            db.add(models.Deadline(student_id=email.student_id,
                                   title=facts.get("summary", email.subject)[:480] or email.subject,
                                   subject=subject or "", due_at=due,
                                   source="email", source_id=source_id,
                                   priority=extraction.priority))
    if extraction.kind == "exam" and facts.get("date"):
        when = datetime.fromisoformat(facts["date"]).replace(tzinfo=timezone.utc)
        db.add(models.Announcement(student_id=email.student_id, title=email.subject,
                                   body=facts.get("summary", email.body[:1000]),
                                   source="email", source_id=f"email:{email.id}",
                                   priority=extraction.priority))
        db.add(models.Exam(student_id=email.student_id, subject=subject or "General",
                           title=email.subject, exam_at=when, source="email"))
    if extraction.kind in ("announcement", "academic_notice", "event", "placement",
                           "timetable_change", "room_change"):
        db.add(models.Announcement(student_id=email.student_id, title=email.subject,
                                   body=facts.get("summary", email.body[:1000]),
                                   source="email", source_id=f"email:{email.id}",
                                   priority=extraction.priority))
    db.commit()


class GmailSource:
    """Production Gmail adapter (OAuth access token, read-only)."""

    name = "gmail"

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    def _get(self, url: str, params: dict | None = None):
        resp = httpx.get(url, headers={"Authorization": f"Bearer {self._token}"},
                         params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def fetch(self, db: Session, student_id: int, max_results: int = 20,
              days: int = 7) -> list[RawItem]:
        listing = self._get("https://gmail.googleapis.com/gmail/v1/users/me/messages",
                            {"maxResults": max(1, min(max_results, 100)),
                             "q": f"newer_than:{max(1, min(days, 30))}d"})
        items = []
        for entry in listing.get("messages", []):
            full = self._get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{entry['id']}",
                             {"format": "full"})
            headers = {h["name"].lower(): h.get("value", "")
                       for h in full.get("payload", {}).get("headers", [])}
            snippet = full.get("snippet", "")
            internal_ms = int(full.get("internalDate", "0"))
            items.append(RawItem(
                external_id=f"gmail:{entry['id']}", title=headers.get("subject", "(no subject)"),
                body=snippet, sender=headers.get("from", ""),
                received_at=datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc)))
        return items


def gmail_auth_url(client_id: str, redirect_uri: str, state: str = "",
                   extra_scope: str = "", gmail: bool = True) -> str:
    from urllib.parse import urlencode
    scope = "openid email profile"
    if gmail:
        scope += " https://www.googleapis.com/auth/gmail.readonly"
    if extra_scope:
        scope += f" {extra_scope}"
    params = {
        "client_id": client_id, "redirect_uri": redirect_uri,
        "response_type": "code", "scope": scope,
        "access_type": "offline", "prompt": "consent"}
    if state:
        params["state"] = state
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def gmail_exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id, "client_secret": client_secret, "code": code,
        "grant_type": "authorization_code", "redirect_uri": redirect_uri}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def google_userinfo(access_token: str) -> dict:
    resp = httpx.get("https://openidconnect.googleapis.com/v1/userinfo",
                     headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    resp.raise_for_status()
    return resp.json()
