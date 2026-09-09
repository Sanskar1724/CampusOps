"""CampusOps configuration. Env-driven; the Caspian SDK never reads .env itself,
so every value is passed explicitly to `Caspian(...)` / `channels.add(...)`."""

from __future__ import annotations

import os

CASPIAN_API_KEY = os.environ.get("CASPIAN_API_KEY", "")
CASPIAN_BASE_URL = os.environ.get("CASPIAN_BASE_URL", "https://api.trycaspianai.com")
CAMPUSOPS_MAILBOX = os.environ.get("CAMPUSOPS_MAILBOX", "")
CASPIAN_ALLOWED_SENDERS = {
    s.strip()
    for s in os.environ.get("CASPIAN_ALLOWED_SENDERS", "").split(",")
    if s.strip()
}

HELLO_TRIGGER = "hello campusops"
HELLO_REPLY = "Hello! I'm CampusOps, your personal academic agent."
FALLBACK_REPLY = (
    "Hi! I'm CampusOps. Say 'Hello CampusOps' to check I'm alive — "
    "more academic skills land here as the agent grows."
)
