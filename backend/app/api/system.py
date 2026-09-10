"""Self-check board: one glance at whether every backend connection is alive.
Secrets are never returned — only ok/fail plus the fix hint."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app import models, security
from backend.app.db import get_db

router = APIRouter(prefix="/api/system", tags=["system"])
Me = security.get_current_student


def _check(name: str, ok: bool, hint: str = "", extra: str = "") -> dict:
    return {"name": name, "ok": ok, "hint": hint, "detail": extra}


@router.get("/status")
def status(db: Session = Depends(get_db), student: models.Student = Depends(Me)):
    checks = []

    try:
        db.execute(text("SELECT 1"))
        checks.append(_check("database", True, extra=type(db.bind).__name__))
    except Exception as exc:
        checks.append(_check("database", False, "Check DATABASE_URL.", str(exc)[:120]))

    model = os.environ.get("MODEL", "")
    if os.environ.get("OPENAI_API_KEY"):
        checks.append(_check("ai_model", True, extra=model or "default"))
    else:
        checks.append(_check("ai_model", False, "Set OPENAI_API_KEY (facts-only mode)."))

    if os.environ.get("CASPIAN_API_KEY"):
        try:
            resp = httpx.get("https://api.trycaspianai.com/v1/channels",
                             headers={"Authorization": f"Bearer {os.environ['CASPIAN_API_KEY']}"},
                             timeout=8)
            ok = resp.status_code in (200, 401, 403)
            checks.append(_check("caspian_gateway", ok,
                                 "" if ok else "Gateway unreachable from this network."))
        except Exception as exc:
            checks.append(_check("caspian_gateway", False,
                                 "Gateway unreachable from this network.", str(exc)[:120]))
    else:
        checks.append(_check("caspian_gateway", False, "Set CASPIAN_API_KEY."))

    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        try:
            resp = httpx.get(
                f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/getMe",
                timeout=8).json()
            ok = bool(resp.get("ok"))
            checks.append(_check("telegram", ok,
                                 "" if ok else "Token rejected by Telegram.",
                                 f"@{resp.get('result', {}).get('username', '')}" if ok else ""))
        except Exception as exc:
            checks.append(_check("telegram", False,
                                 "Telegram unreachable from this network.", str(exc)[:120]))
    else:
        checks.append(_check("telegram", False, "Set TELEGRAM_BOT_TOKEN."))

    if os.environ.get("GMAIL_CLIENT_ID"):
        from sqlalchemy import select  # noqa: E402
        connected = db.scalar(select(models.Integration).where(
            models.Integration.student_id == student.id,
            models.Integration.provider == "gmail",
            models.Integration.status == "connected")) is not None
        checks.append(_check("gmail", connected,
                             "Settings → Connect Gmail." if not connected else ""))
    else:
        checks.append(_check("gmail", False, "Set GMAIL_CLIENT_ID/SECRET on the server."))

    return {"all_ok": all(c["ok"] for c in checks), "checks": checks}
