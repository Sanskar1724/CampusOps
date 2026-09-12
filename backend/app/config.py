"""CampusOps configuration. Env-driven; the Caspian SDK never reads .env itself,
so every value is passed explicitly to `Caspian(...)` / `channels.add(...)`."""

from __future__ import annotations

import os

CASPIAN_API_KEY = os.environ.get("CASPIAN_API_KEY", "")
CASPIAN_BASE_URL = os.environ.get("CASPIAN_BASE_URL", "https://api.trycaspianai.com")
CAMPUSOPS_MAILBOX = os.environ.get("CAMPUSOPS_MAILBOX", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CASPIAN_ALLOWED_SENDERS = {
    s.strip()
    for s in os.environ.get("CASPIAN_ALLOWED_SENDERS", "").split(",")
    if s.strip()
}

HELLO_TRIGGER = "hello campusops"
HELLO_REPLY = (
    "Hello! I'm CampusOps 🎓 — your academic co-pilot. I track your classes, "
    "deadlines & inbox. Try: 'What should I focus on today?' or 'Did my timetable change?'"
)
FALLBACK_REPLY = (
    "Hi! I'm CampusOps 🎓. Ask me 'What should I focus on today?', "
    "'What's my next class?', or say 'Hello CampusOps' to check I'm alive."
)
