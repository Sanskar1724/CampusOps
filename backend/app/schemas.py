"""Pydantic schemas for every resource."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    full_name: str = ""
    prn: str
    department: str = ""
    division: str = ""
    batch: str = ""
    roll_number: str = ""
    semester: str = ""
    course: str = ""
    college_email: str
    password: str = Field(min_length=6)


class LoginIn(BaseModel):
    college_email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StudentOut(BaseModel):
    id: int
    full_name: str
    prn: str
    department: str
    division: str
    batch: str
    roll_number: str
    semester: str
    course: str
    college_email: str
    onboarding_status: str
    is_demo: bool

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    division: str | None = None
    batch: str | None = None
    roll_number: str | None = None
    semester: str | None = None
    course: str | None = None


class OnboardingIn(BaseModel):
    text: str


class TimetableIn(BaseModel):
    day: int = Field(ge=0, le=6)
    subject: str
    start_time: str
    end_time: str
    room: str = ""
    faculty: str = ""
    division: str = ""
    batch: str = ""


class TimetableOut(TimetableIn):
    id: int

    model_config = {"from_attributes": True}


class DeadlineIn(BaseModel):
    title: str
    subject: str = ""
    due_at: datetime | None = None
    priority: str = "normal"


class TaskIn(BaseModel):
    title: str
    detail: str = ""
    due_at: datetime | None = None


class ReminderIn(BaseModel):
    text: str
    remind_at: datetime


class ChatIn(BaseModel):
    text: str


class ChatOut(BaseModel):
    reply: str


class MemoryIn(BaseModel):
    mem_type: str = "fact"
    key: str
    value: str
    confidence: float = 1.0


class GmailCallbackIn(BaseModel):
    code: str


class GoogleCallbackIn(BaseModel):
    code: str
    redirect_uri: str
