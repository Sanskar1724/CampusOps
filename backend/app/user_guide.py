"""User-guide injection: the agent answers with UI guidance, not just facts.

The full guide lives in docs/USER_GUIDE.md (single source; also served at
GET /api/help). The agent gets a compact pointer block so replies can say
*where* to tap, e.g. 'Timetable → My classes' instead of just describing."""

from __future__ import annotations

from pathlib import Path

GUIDE_POINTER = (
    "APP GUIDE (point the student at these when relevant): "
    "Timetable page defaults to 'My classes' (their batch) with a "
    "'Show all divisions' toggle; hide classes via chat ('hide OS') or "
    "unhide ('show everything'); Gmail connects in Settings → Connect Gmail, "
    "then Email → Sync; PDFs/TXT/CSV/XLSX/DOCX/photos upload on Documents "
    "(Re-scan with OCR if a scan reads poorly); notification kinds, quiet "
    "hours, and channel live in Notifications → Preferences; Telegram bot "
    "supports /today /tomorrow /next /deadlines /brief /focus /help plus "
    "quick-action buttons."
)


def load_full_guide() -> str:
    path = Path(__file__).resolve().parent.parent.parent / "docs" / "USER_GUIDE.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return "# CampusOps User Guide\n\n" + GUIDE_POINTER
