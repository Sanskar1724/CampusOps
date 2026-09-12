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
from backend.app.memory import get_or_create_conversation, log_message


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
            log_message(db, conv.id, "user", msg.text)
            try:
                reply = handle_turn(db, student, expand_command(msg.text),
                                    channel=str(channel))
            except Exception:
                traceback.print_exc()
                reply = ("Something went wrong on my side. Your message is saved — "
                         "please try again in a moment.")
            from backend.app.comms.service import FIRST_TIME_GUIDE
            if known is None and str(channel) != "web":
                reply = FIRST_TIME_GUIDE + reply
            log_message(db, conv.id, "agent", reply)
            reply_with_actions(thread, reply)
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
            reply = handle_turn(db, student, question, channel="caspian")
            log_message(db, conv.id, "agent", reply)
            reply_with_actions(thread, reply)
        finally:
            db.close()

    return cx


def handle_text_offline(student_id_sender: str, text: str) -> str:
    """Test seam: run the same pipeline without a live Caspian connection."""
    db = SessionLocal()
    try:
        student = get_or_create_student_for_sender(db, student_id_sender)
        return handle_turn(db, student, text)
    finally:
        db.close()
