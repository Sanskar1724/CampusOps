"""CampusOps Core Agent — minimal seam.

Today this is a pure function so the Caspian handler stays thin and the
web chat can share the exact same brain later. It grows into the tool-using
agent (timetable, deadlines, email, documents, memory) without changing the
comms layer: `comms/` imports this, never the reverse.
"""

from __future__ import annotations

from backend.app import config


def respond_to_text(text: str) -> str:
    """Turn inbound message text into reply text. No I/O, no channel knowledge."""
    if text.strip().lower() == config.HELLO_TRIGGER:
        return config.HELLO_REPLY
    return config.FALLBACK_REPLY
