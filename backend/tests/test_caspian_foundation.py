"""Caspian foundation verification — offline, zero network.

Uses only real SDK classes (`Caspian`, `Thread`, `Message`,
`HandlerContext`, `MemoryInterpreter`). `dispatch=False` means no transport
and no gateway client, so nothing here can touch the network.
"""

import pytest
from caspian import HandlerContext, Message, Thread
from caspian.core.commands import Host

from backend.app import config
from backend.app.agents.core import respond_to_text
from backend.app.comms.client import build_caspian_app

MAILBOX = "campusops-test"


def make_message(text: str, thread_id: str = "thread-test-1",
                 sender: str = "student@example.com") -> Message:
    return Message(
        thread_id=thread_id,  # type: ignore[arg-type]
        text=text,
        chat_kind="dm",  # type: ignore[arg-type]
        sender=sender,
        message_id="msg-1",
    )


def test_hello_brain_reply():
    assert respond_to_text("Hello CampusOps") == config.HELLO_REPLY
    assert respond_to_text("  hello campusops  ") == config.HELLO_REPLY


def test_fallback_brain_reply():
    assert respond_to_text("What is my next class?") == config.FALLBACK_REPLY


def test_handler_runs_full_pipeline_on_real_thread(db_session):
    cx = build_caspian_app(mailbox=MAILBOX, dispatch=False)
    assert len(cx.app.rules) == 2  # message handler + action handler, every channel

    handler_id = next(iter(cx._handlers))  # noqa: SLF001 — test seam
    handler = cx._handlers[handler_id]  # noqa: SLF001

    thread = Thread(thread_id=make_message("x").thread_id)
    handler(thread, make_message("Hello CampusOps"), HandlerContext())
    assert len(thread.commands) == 1
    # New sender enters onboarding first — the reply must be a real question,
    # proving handler → DB → agent → reply works end to end.
    text = getattr(thread.commands[0], "text", "")
    assert text and ("name" in text.lower() or "prn" in text.lower())


def test_inbound_routes_through_real_kernel():
    cx = build_caspian_app(mailbox=MAILBOX, dispatch=False)
    interp = cx.interpret()
    result = interp.run(cx.app, make_message("Hello CampusOps"), channel_name="email")
    hosts = [c for c in result.commands if isinstance(c, Host)]
    assert len(hosts) == 1  # kernel matched the message rule


def test_rule_is_channel_agnostic():
    cx = build_caspian_app(mailbox=MAILBOX, dispatch=False)
    interp = cx.interpret()
    for i, channel in enumerate(("email", "telegram")):
        event = make_message("Hello CampusOps", thread_id=f"thread-{channel}")
        result = interp.run(cx.app, event, channel_name=channel)
        assert any(isinstance(c, Host) for c in result.commands), channel


def test_mailbox_is_required():
    with pytest.raises(ValueError):
        build_caspian_app(mailbox="  ", dispatch=False)


def test_telegram_self_host_builds_offline():
    cx = build_caspian_app(telegram_bot_token="dummy-token-for-build",
                           telegram_via="self-host", dispatch=False)
    assert cx.channels.added() == ["telegram"]
    assert len(cx.app.rules) == 2  # message + action handlers


def test_first_time_sender_gets_guide_once(db_session):
    from backend.app.comms.service import FIRST_TIME_GUIDE
    cx = build_caspian_app(mailbox=MAILBOX, dispatch=False)
    handler = next(iter(cx._handlers.values()))  # noqa: SLF001
    first = Thread(thread_id="guide-thread-1")
    handler(first, make_message("hi there", sender="guide-new@example.com"), HandlerContext())
    text1 = getattr(first.commands[0], "text", "")
    assert text1.startswith("👋 Welcome to CampusOps")
    assert "PRN" in text1  # first message became their name; onboarding continues
    second = Thread(thread_id="guide-thread-1")
    handler(second, make_message("Rahul", sender="guide-new@example.com"), HandlerContext())
    text2 = getattr(second.commands[0], "text", "")
    assert not text2.startswith("👋 Welcome to CampusOps")


def test_reply_formatting_and_buttons():
    from backend.app.comms.service import format_reply, quick_buttons
    assert format_reply("a\n\n\n\nb") == "a\n\nb"
    long_text = "x\n" * 5000
    assert len(format_reply(long_text)) < len(long_text)
    assert "continued" in format_reply(long_text)
    buttons = quick_buttons()
    assert len(buttons) == 7
    assert {b.data for b in buttons} >= {"cmd:today", "cmd:week", "cmd:reminders", "cmd:help"}
