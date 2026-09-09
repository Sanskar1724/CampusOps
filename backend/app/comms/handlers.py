"""Caspian message handlers. One handler answers every connected channel."""

from __future__ import annotations

from caspian import Caspian, HandlerContext, Message, Thread

from backend.app.agents.core import respond_to_text
from backend.app.comms.service import reply_text


def register(cx: Caspian) -> Caspian:
    """Attach the single inbound-message rule. No channel filter on purpose:
    the same code answers wherever the student reaches us."""

    @cx.on_message({"overlap": "queue"})
    def handle_message(thread: Thread, msg: Message, ctx: HandlerContext) -> None:
        reply_text(thread, respond_to_text(msg.text))

    return cx
