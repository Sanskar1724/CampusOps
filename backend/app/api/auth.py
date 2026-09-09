"""Auth routes: register / login / me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app import models, schemas, security
from backend.app.db import get_db

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
