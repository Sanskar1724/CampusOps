"""Caspian message handlers. One handler answers every connected channel.

Identity: `msg.sender` maps to `students.caspian_sender`. Unknown senders get
a placeholder profile and enter conversational onboarding; nothing from one
sender is ever visible to another (all downstream queries filter by student).
"""

from __future__ import annotations

import traceback

from caspian import Caspian, HandlerContext, Message, Thread
from sqlalchemy import select

from backend.app import config, models
from backend.app.agents.core import handle_turn
from backend.app.comms.service import expand_command, reply_with_actions
from backend.app.db import SessionLocal
from backend.app.memory import (
    get_or_create_conversation,
    log_message,
    recent_messages,
)

import httpx


def get_or_create_student_for_sender(db, sender: str) -> models.Student:
    student = db.scalar(select(models.Student).where(
        models.Student.caspian_sender == sender))
    if student:
        return student
    tag = sender.strip() or "unknown"
    student = models.Student(
        full_name="", prn=f"pending:{tag}", college_email=f"pending:{tag}",
        caspian_sender=sender, onboarding_status="pending",
        onboarding_step="full_name")
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def _allowed(sender: str) -> bool:
    return not config.CASPIAN_ALLOWED_SENDERS or sender in config.CASPIAN_ALLOWED_SENDERS


def _telegram_chat_id(msg: Message) -> str:
    """Find the Telegram chat id in the raw payload (shape varies by path:
    poll vs webhook, direct vs nested `message`). Stored so proactive
    notifications can go out over the Bot API when the gateway is blocked."""
    raw = getattr(msg, "raw", None) or {}
    if not isinstance(raw, dict):
        return ""
    candidates = [
        raw.get("chat_id"),
        (raw.get("chat") or {}).get("id") if isinstance(raw.get("chat"), dict) else None,
        ((raw.get("message") or {}).get("chat") or {}).get("id")
        if isinstance(raw.get("message"), dict) else None,
    ]
    for value in candidates:
        if value:
            return str(value)
    return ""


def _download_telegram_attachment(att) -> tuple[bytes, str, str]:
    """Download attachment bytes via Caspian URL or Telegram Bot API fallback.
    Returns (data, filename, mime_type)."""
    filename = getattr(att, "filename", "") or f"telegram_{getattr(att, 'type', 'file')}_{getattr(att, 'file_id', '')[:8] or 'doc'}"
    mime = getattr(att, "mime_type", "") or ""
    # Infer mime from filename if missing
    if not mime:
        low = filename.lower()
        if low.endswith(".pdf"):
            mime = "application/pdf"
        elif low.endswith((".png", ".jpg", ".jpeg")):
            mime = "image/jpeg" if low.endswith((".jpg", ".jpeg")) else "image/png"
        elif low.endswith(".txt"):
            mime = "text/plain"
        elif low.endswith(".csv"):
            mime = "text/csv"
        elif low.endswith(".xlsx"):
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif low.endswith(".docx"):
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    url = getattr(att, "url", "") or ""
    if url:
        # Caspian may provide direct URL; fetch it
        try:
            resp = httpx.get(url, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            return resp.content, filename, mime
        except Exception as e:
            raise ValueError(f"Failed to download {filename}: {e}")

    # Fallback: Telegram Bot API getFile via file_id
    file_id = getattr(att, "file_id", "") or ""
    if file_id and config.TELEGRAM_BOT_TOKEN:
        try:
            info = httpx.get(
                f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getFile",
                params={"file_id": file_id},
                timeout=20,
            ).json()
            if not info.get("ok"):
                raise ValueError(f"Telegram getFile failed: {info}")
            file_path = info["result"]["file_path"]
            # Preserve real filename extension if Telegram gives generic path
            if not filename or filename.startswith("telegram_"):
                # Use file_path basename as filename fallback
                import os as _os
                real_name = _os.path.basename(file_path)
                if real_name:
                    filename = real_name
            dl_url = f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}/{file_path}"
            resp = httpx.get(dl_url, timeout=60)
            resp.raise_for_status()
            return resp.content, filename, mime
        except Exception as e:
            raise ValueError(f"Telegram download failed for {filename}: {e}")

    raise ValueError(f"No download URL for {filename} (no url/file_id)")


def _handle_telegram_documents(db, student, msg: Message, thread) -> str | None:
    """If message has attachments (Telegram doc/photo), ingest like website upload.
    Returns reply string if handled, else None to continue normal chat."""
    attachments = getattr(msg, "attachments", None) or ()
    if not attachments:
        return None

    # Only handle document-like attachments; ignore stickers/voice etc gracefully
    supported_types = {"file", "photo", "document", "image"}
    docs = [a for a in attachments if getattr(a, "type", "file") in supported_types or getattr(a, "filename", "")]
    # If no supported docs but attachments exist, still try first attachment (maybe file without type)
    if not docs and attachments:
        docs = list(attachments)[:1]

    if not docs:
        return None

    from backend.app.ingestion.pdf_source import ingest_document
    from backend.app.llm import safe_json_loads

    replies = []
    for att in docs:
        try:
            data, filename, mime = _download_telegram_attachment(att)
            # Use ingest_document pipeline (same as website)
            doc = ingest_document(db, student.id, filename, mime, data)
            facts = safe_json_loads(doc.facts_json, {})
            method = facts.get("extraction", "text-layer")
            # Build concise, formatted reply like website
            hint = ""
            if method == "vision-ocr":
                hint = " (scanned — read with vision OCR)"
            elif method.startswith("ocr-failed"):
                hint = " (scan was hard to read — try a clearer photo or text PDF)"

            # Summarize extracted facts concisely
            subjects = ", ".join(facts.get("subjects", [])[:3]) or facts.get("subject", "") or "—"
            dates = ", ".join(facts.get("dates", [])[:3]) or "—"
            kind = facts.get("kind", "document")
            reply = (
                f"✅ Got *{filename}* — {kind}{hint}\n"
                f"📄 Subjects: {subjects}\n"
                f"📅 Dates: {dates}\n"
                f"🔍 Search it anytime: ask \"when is the {subjects.split(',')[0].strip() if subjects != '—' else 'exam'}?\" in chat."
            )
            # Strip markdown markers via service formatting will happen later, but keep for web
            # For Telegram, we'll have markdown stripped in reply path, so use plain
            replies.append(reply)
        except Exception as e:
            # Friendly error, mention supported types
            replies.append(f"⚠️ Could not process {getattr(att, 'filename', 'file')}: {e}\nSupported: PDF, TXT, CSV, XLSX, DOCX, PNG, JPG (15 MB / 5 MB limits).")

    if replies:
        return "\n\n".join(replies)
    return None


def register(cx: Caspian) -> Caspian:
    """Attach the single inbound-message rule. No channel filter on purpose:
    the same code answers wherever the student reaches us."""

    @cx.on_message({"overlap": "queue"})
    def handle_message(thread: Thread, msg: Message, ctx: HandlerContext) -> None:
        if not _allowed(msg.sender):
            return
        db = SessionLocal()
        try:
            known = db.scalar(select(models.Student).where(
                models.Student.caspian_sender == (msg.sender or "unknown")))
            student = get_or_create_student_for_sender(db, msg.sender or "unknown")
            student.caspian_thread_id = str(msg.thread_id)
            chat_id = _telegram_chat_id(msg)
            if chat_id:
                student.telegram_chat_id = chat_id
            db.commit()
            channel = (msg.metadata or {}).get("channel", "caspian")
            conv = get_or_create_conversation(
                db, channel=str(channel), thread_id=str(msg.thread_id),
                sender=msg.sender, student_id=student.id)
            history = recent_messages(db, conv.id, limit=6)
            log_message(db, conv.id, "user", msg.text or "[attachment]")
            # /link <code> — explicit account linking for returning users
            _txt = (msg.text or "").strip()
            if _txt.lower().startswith("/link"):
                try:
                    from backend.app.api.deps import get_prefs  # noqa
                    parts = _txt.split()
                    if len(parts) < 2:
                        reply = "Send /link <6-digit code> — generate the code on the web: Profile → Link Telegram."
                    else:
                        code = parts[1].strip()
                        # Find owner who generated this code
                        from backend.app.models import StudentPreference
                        prefs = db.scalars(select(StudentPreference).where(
                            StudentPreference.key == "telegram_link_code")).all()
                        owner = None
                        for pref in prefs:
                            try:
                                import json as _json
                                from datetime import datetime as _dt
                                data = _json.loads(pref.value)
                                if data.get("code") == code:
                                    exp = _dt.fromisoformat(data.get("expires_at", ""))
                                    if exp.tzinfo is None:
                                        from datetime import timezone as _tz
                                        exp = exp.replace(tzinfo=_tz.utc)
                                    from backend.app.models import utcnow as _utcnow
                                    if exp > _utcnow():
                                        owner = db.get(models.Student, pref.student_id)
                                        # consume code
                                        db.delete(pref)
                                        db.commit()
                                        break
                                    else:
                                        db.delete(pref)
                                        db.commit()
                            except Exception:
                                continue
                        if not owner:
                            reply = "❌ Invalid or expired code. Generate a fresh one on the web: Profile → Link Telegram (valid 10 min)."
                        elif owner.id == student.id:
                            reply = "✅ This Telegram is already linked to your account."
                        else:
                            # Merge: keep web account as primary, attach Telegram identity
                            owner.caspian_sender = student.caspian_sender or owner.caspian_sender
                            owner.caspian_thread_id = student.caspian_thread_id or owner.caspian_thread_id
                            if getattr(student, "telegram_chat_id", None):
                                owner.telegram_chat_id = student.telegram_chat_id
                            elif chat_id:
                                owner.telegram_chat_id = chat_id
                            # Remember link time
                            from backend.app.api.deps import set_pref
                            import json as _json2
                            set_pref(db, owner.id, "telegram_linked_at", _utcnow().isoformat() if ' _utcnow' not in locals() else __import__('backend.app.models', fromlist=['utcnow']).utcnow().isoformat())
                            # Delete Telegram placeholder
                            placeholder_id = student.id
                            db.delete(student)
                            db.commit()
                            reply = (
                                f"✅ Linked! Your Telegram is now connected to *{owner.full_name}* ({owner.college_email}).\n"
                                f"Your timetable, deadlines & docs are synced — web and Telegram share the same data. "
                                f"Try /today or 'What is my next class?'"
                            )
                            # Switch student reference for logging
                            student = owner
                    from backend.app.comms.service import FIRST_TIME_GUIDE
                    if known is None and str(channel) != "web":
                        # Do not prepend guide for link command — keep it clean
                        pass
                    log_message(db, conv.id, "agent", reply)
                    # Use plain reply for link (no buttons needed)
                    from backend.app.comms.service import format_reply
                    thread.post(format_reply(reply))
                    return
                except Exception:
                    traceback.print_exc()
            # Telegram document path: same pipeline as website upload
            if getattr(msg, "attachments", None):
                try:
                    doc_reply = _handle_telegram_documents(db, student, msg, thread)
                    if doc_reply is not None:
                        from backend.app.comms.service import FIRST_TIME_GUIDE
                        if known is None and str(channel) != "web":
                            doc_reply = FIRST_TIME_GUIDE + doc_reply
                        log_message(db, conv.id, "agent", doc_reply)
                        reply_with_actions(thread, doc_reply)
                        return
                except Exception:
                    traceback.print_exc()
                    # fall through to normal chat on unexpected error
            try:
                reply = handle_turn(db, student, expand_command(msg.text or ""),
                                    channel=str(channel), history=history)
            except Exception:
                db.rollback()
                traceback.print_exc()
                reply = ("Something went wrong on my side. Your message is saved — "
                         "please try again in a moment.")
            from backend.app.comms.service import FIRST_TIME_GUIDE
            if known is None and str(channel) != "web":
                reply = FIRST_TIME_GUIDE + reply
            log_message(db, conv.id, "agent", reply)
            reply_with_actions(thread, reply)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @cx.on_action({"overlap": "queue"})
    def handle_action(thread: Thread, action, ctx: HandlerContext) -> None:
        """Quick-action button taps (Telegram keyboards) route back into the
        same agent as the equivalent question."""
        from backend.app.comms.service import COMMAND_TEXT
        data = str(getattr(action, "data", "") or "")
        name = data.split(":", 1)[1] if data.startswith("cmd:") else ""
        question = COMMAND_TEXT.get(name)
        if not question:
            return
        db = SessionLocal()
        try:
            student = get_or_create_student_for_sender(
                db, getattr(action, "sender", "") or "unknown")
            student.caspian_thread_id = str(getattr(action, "thread_id", ""))
            db.commit()
            conv = get_or_create_conversation(
                db, channel="caspian",
                thread_id=str(getattr(action, "thread_id", "")),
                student_id=student.id)
            log_message(db, conv.id, "user", f"[{name}]")
            history = recent_messages(db, conv.id, limit=6)[:-1]
            reply = handle_turn(db, student, question, channel="caspian", history=history)
            log_message(db, conv.id, "agent", reply)
            reply_with_actions(thread, reply)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    return cx


def handle_text_offline(student_id_sender: str, text: str) -> str:
    """Test seam: run the same pipeline without a live Caspian connection."""
    db = SessionLocal()
    try:
        student = get_or_create_student_for_sender(db, student_id_sender)
        return handle_turn(db, student, text)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
