"""CommunicationService: the only place that touches Caspian `Thread` sends.

Business logic calls these helpers; it never imports `caspian` itself.
Proactive sends (`send`/`initiate`/`schedule`) arrive with the scheduler work,
not here — this module only covers what the live receive→reply loop needs.
"""

from __future__ import annotations

from caspian import Thread


def reply_text(thread: Thread, text: str) -> None:
    """Threaded reply to the message that opened this turn."""
    thread.post(text)
