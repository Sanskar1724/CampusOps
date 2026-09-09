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


def make_message(text: str, thread_id: str = "thread-test-1") -> Message:
    return Message(
        thread_id=thread_id,  # type: ignore[arg-type]
        text=text,
        chat_kind="dm",  # type: ignore[arg-type]
        sender="student@example.com",
        message_id="msg-1",
    )


def test_hello_brain_reply():
    assert respond_to_text("Hello CampusOps") == config.HELLO_REPLY
    assert respond_to_text("  hello campusops  ") == config.HELLO_REPLY


def test_fallback_brain_reply():
    assert respond_to_text("What is my next class?") == config.FALLBACK_REPLY


def test_handler_posts_reply_on_real_thread():
    cx = build_caspian_app(mailbox=MAILBOX, dispatch=False)
    assert len(cx.app.rules) == 1  # one handler, every channel

    handler_id = next(iter(cx._handlers))  # noqa: SLF001 — test seam
    handler = cx._handlers[handler_id]  # noqa: SLF001

    thread = Thread(thread_id=make_message("x").thread_id)
    handler(thread, make_message("Hello CampusOps"), HandlerContext())
    assert len(thread.commands) == 1
    assert getattr(thread.commands[0], "text", "") == config.HELLO_REPLY


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
