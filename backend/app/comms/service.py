"""CommunicationService: the only place that touches Caspian `Thread` sends.

Business logic calls these helpers; it never imports `caspian` itself.
Proactive sends (`send`/`initiate`/`schedule`) arrive with the scheduler work,
not here — this module only covers what the live receive→reply loop needs.
"""

from __future__ import annotations

from caspian import Thread
from caspian import Button as _Button

#: Quick actions under every agent reply (render as Telegram keyboards,
#: degrade gracefully elsewhere). `data` routes back through on_action.
QUICK_ACTIONS: tuple[tuple[str, str], ...] = (
    ("📅 Today", "cmd:today"),
    ("➡️ Next class", "cmd:next"),
    ("⏰ Deadlines", "cmd:deadlines"),
    ("🎯 Focus", "cmd:focus"),
    ("❓ Help", "cmd:help"),
)
#: /commands (Telegram + anywhere) mapped to plain agent questions.
COMMAND_TEXT: dict[str, str] = {
    "start": "Hello CampusOps",
    "help": ("I can: show today's/tomorrow's classes, next class, deadlines, exams, "
             "email updates, search documents, set reminders/tasks, hide classes "
             "('hide OS'), and show them again. Try the buttons below! "
             "Full guide: Help page → USER_GUIDE."),
    "today": "What do I have today?",
    "tomorrow": "What do I have tomorrow?",
    "next": "What is my next class?",
    "deadlines": "What assignments are coming up?",
    "exams": "What exams are coming up?",
    "brief": "Give me my daily brief",
    "focus": "What should I focus on today?",
    "week": "What do I have this week?",
    "reminders": "Show my reminders",
}


def expand_command(text: str) -> str:
    """Turn '/today@Bot extra' into the agent question. Non-commands pass through."""
    stripped = text.strip()
    if not stripped.startswith("/"):
        return text
    name = stripped[1:].split()[0].split("@")[0].lower()
    return COMMAND_TEXT.get(name, text)


def quick_buttons() -> tuple:
    return tuple(_Button(label=label, data=data) for label, data in QUICK_ACTIONS)


def reply_text(thread: Thread, text: str) -> None:
    """Threaded reply to the message that opened this turn."""
    thread.post(text)


def reply_with_actions(thread: Thread, text: str) -> None:
    """Reply + quick-action buttons (Telegram keyboards; harmless elsewhere)."""
    try:
        thread.post(text, actions=quick_buttons())
    except Exception:
        thread.post(text)
