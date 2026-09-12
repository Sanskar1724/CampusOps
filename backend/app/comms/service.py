"""CommunicationService: the only place that touches Caspian `Thread` sends.

Business logic calls these helpers; it never imports `caspian` itself.
Proactive sends (`send`/`initiate`/`schedule`) arrive with the scheduler work,
not here — this module only covers what the live receive→reply loop needs.
"""

from __future__ import annotations

from caspian import Thread
from caspian import Button as _Button

#: The 4 main features on the Telegram keyboard. Everything else lives
#: behind /commands (see BOT_COMMANDS) so the keyboard stays thumb-sized.
QUICK_ACTIONS: tuple[tuple[str, str], ...] = (
    ("📅 Today", "cmd:today"),
    ("➡️ Next class", "cmd:next"),
    ("⏰ Deadlines", "cmd:deadlines"),
    ("🎯 Focus", "cmd:focus"),
)

#: BotFather "/" menu: typing "/" lists every capability. Synced to Telegram
#: at runner startup via set_bot_menu() — idempotent, safe to re-run.
BOT_COMMANDS: tuple[tuple[str, str], ...] = (
    ("today", "Today's classes"),
    ("tomorrow", "Tomorrow's classes"),
    ("week", "Whole week"),
    ("next", "Next class"),
    ("deadlines", "Upcoming deadlines"),
    ("exams", "Upcoming exams"),
    ("reminders", "My reminders"),
    ("brief", "Daily brief"),
    ("focus", "What to focus on now"),
    ("help", "What can you do?"),
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


#: First-contact guide for brand-new senders (Telegram/email). Sent once,
#: together with the first onboarding question — never again.
FIRST_TIME_GUIDE = (
    "👋 Welcome to CampusOps — your personal academic agent!\n\n"
    "Here's what I can do for you:\n"
    "📅 Classes — today, tomorrow, next class, whole week\n"
    "⏰ Deadlines, exams & reminders (I can set them too)\n"
    "📧 College email updates & room-change alerts\n"
    "🙈 Hide things you don't want: 'hide OS', 'don't show Saturdays'\n\n"
    "Tap a button below anytime, or try /help for all commands.\n"
    "Let's get you set up — "
)

import re as _re


def strip_markdown(text: str) -> str:
    """Telegram's Bot API gets plain text (no parse_mode), so `**bold**`,
    backticks, and `__underline__` would show up literally — remove the
    markers but keep the words and the emoji/line structure."""
    text = _re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = _re.sub(r"__(.+?)__", r"\1", text)
    return text.replace("`", "")


def format_reply(text: str, limit: int = 3500) -> str:
    """Tidy agent text for chat channels: collapse runaway blank lines,
    strip markdown markers (plain-text channels), trim trailing space, and
    cap length so long answers arrive whole instead of cut off mid-sentence."""
    tidy = _re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    tidy = strip_markdown(tidy)
    if len(tidy) <= limit:
        return tidy
    cut = tidy[:limit].rsplit("\n", 1)[0]
    return cut + "\n\n…(continued in the web chat → AI Chat)"


def set_bot_menu(bot_token: str) -> bool:
    """Publish the / command menu to Telegram (typing '/' lists everything).
    Idempotent — returns True when Telegram acknowledges."""
    import httpx
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/setMyCommands",
            json={"commands": [{"command": name, "description": desc}
                               for name, desc in BOT_COMMANDS]},
            timeout=20)
        return bool(resp.json().get("ok"))
    except Exception:
        return False


def reply_text(thread: Thread, text: str) -> None:
    """Threaded reply to the message that opened this turn."""
    thread.post(format_reply(text))


def reply_with_actions(thread: Thread, text: str) -> None:
    """Reply + quick-action buttons (Telegram keyboards; harmless elsewhere)."""
    try:
        thread.post(format_reply(text), actions=quick_buttons())
    except Exception:
        thread.post(format_reply(text))
