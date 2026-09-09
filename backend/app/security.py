"""Authentication: PBKDF2 password hashing (stdlib) + JWT sessions.

 isolating rule lives here too: every query a route makes must be scoped with
 `owned(query, student)` helpers — the current student comes only from the
 verified JWT, never from request payloads.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.db import get_db

ALGORITHM = "HS256"
SECRET = os.environ.get("APP_SECRET_KEY", "dev-only-change-me")
TOKEN_HOURS = 24 * 7
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(check, digest)


def make_token(student_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(student_id), "exp": exp}, SECRET, algorithm=ALGORITHM)


def make_oauth_state(student_id: int) -> str:
    """Short-lived signed state for OAuth redirects (binds flow to a student)."""
    exp = datetime.now(timezone.utc) + timedelta(minutes=10)
    return jwt.encode({"sub": str(student_id), "exp": exp, "kind": "oauth"},
                      SECRET, algorithm=ALGORITHM)


def read_oauth_state(state: str) -> int:
    try:
        payload = jwt.decode(state, SECRET, algorithms=[ALGORITHM])
        if payload.get("kind") != "oauth":
            raise ValueError("not oauth state")
        return int(payload.get("sub", "0"))
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Bad OAuth state: {exc}")


def get_current_student(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.Student:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=[ALGORITHM])
        student_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad token")
    student = db.get(models.Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown student")
    return student
