"""Auth routes: register / login / me / Google sign-in."""

from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app import models, schemas, security
from backend.app.db import get_db
from backend.app.ingestion import email_source

router = APIRouter(prefix="/api/auth", tags=["auth"])

PROFILE_FIELDS = ["full_name", "prn", "department", "division", "batch",
                  "roll_number", "semester", "course", "college_email"]


@router.post("/register", response_model=schemas.TokenOut)
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    clash = db.scalar(select(models.Student).where(or_(
        models.Student.prn == payload.prn,
        models.Student.college_email == payload.college_email)))
    if clash:
        raise HTTPException(status_code=409, detail="PRN or email already registered")
    student = models.Student(
        full_name=payload.full_name, prn=payload.prn, department=payload.department,
        division=payload.division, batch=payload.batch, roll_number=payload.roll_number,
        semester=payload.semester, course=payload.course,
        college_email=payload.college_email,
        password_hash=security.hash_password(payload.password))
    filled = all(getattr(payload, f) for f in PROFILE_FIELDS)
    student.onboarding_status = "done" if filled else "pending"
    student.onboarding_step = "done" if filled else "full_name"
    db.add(student)
    db.commit()
    db.refresh(student)
    return {"access_token": security.make_token(student.id)}


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    student = db.scalar(select(models.Student).where(
        models.Student.college_email == payload.college_email))
    if not student or not security.verify_password(payload.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": security.make_token(student.id)}


@router.get("/me", response_model=schemas.StudentOut)
def me(student: models.Student = Depends(security.get_current_student)):
    return student


def _google_env() -> tuple[str, str]:
    client_id = os.environ.get("GMAIL_CLIENT_ID", "")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise HTTPException(status_code=409, detail="Google OAuth not configured on the server.")
    return client_id, client_secret


@router.get("/google/url")
def google_url(redirect_uri: str):
    """Step 1 of Sign in with Google: frontend redirects the browser here.

    Minimal scopes (identity only) — Gmail access is asked separately in
    Settings, so sign-in never trips restricted-scope policy."""
    client_id, _ = _google_env()
    return {"auth_url": email_source.gmail_auth_url(client_id, redirect_uri, gmail=False)}


@router.post("/google/callback", response_model=schemas.TokenOut)
def google_callback(payload: schemas.GoogleCallbackIn, db: Session = Depends(get_db)):
    """Step 2: frontend POSTs the `code` Google sent to its redirect page."""
    client_id, client_secret = _google_env()
    try:
        tokens = email_source.gmail_exchange_code(
            client_id, client_secret, payload.code, payload.redirect_uri)
        info = email_source.google_userinfo(tokens["access_token"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google sign-in failed: {exc}")
    email = (info.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=502, detail="Google did not return an email address.")
    student = db.scalar(select(models.Student).where(models.Student.college_email == email))
    if student is None:
        student = models.Student(
            full_name=str(info.get("name", ""))[:200], prn=f"google:{info.get('sub', email)}",
            college_email=email,
            password_hash=security.hash_password(secrets.token_hex(16)),
            onboarding_status="pending", onboarding_step="full_name")
        db.add(student)
        db.commit()
        db.refresh(student)
    return {"access_token": security.make_token(student.id)}
