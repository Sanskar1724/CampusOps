# CampusOps — Personal Academic Agent for Students

> **Status: Caspian receive→reply loop implemented and tested offline.**
> See `docs/00-caspian-capability-map.md`, `docs/01-architecture.md`, and
> `docs/caspian-foundation.md`. Live gateway verification still needs
> `CASPIAN_API_KEY` + `CAMPUSOPS_MAILBOX` and has not run yet.

## Vision

CampusOps collects permitted academic information (college email, timetable,
PDFs/notices in V1), understands it, stores it in layered academic memory,
reasons with the student's personal context, and proactively helps the student —
with **Caspian as the communication foundation**, not an add-on.

## Caspian-first rule

- All student messaging goes through the **real Caspian SDK v1.x**
  (`pip install caspian-sdk`, `from caspian import Caspian`).
- Business logic never branches on `if telegram: / if discord:`.
- One `CampusOps Core Agent` serves Caspian chat, web chat, and future channels.
- Verified against installed `caspian-sdk==1.0.2` on Python 3.14 (2026-09-09).
  Full capability map: `docs/00-caspian-capability-map.md`.

## V1 scope

Sources: college email (Gmail API/OAuth, never passwords), timetable
(upload/manual), PDFs/documents. **No Moodle, no WhatsApp group ingestion in V1**
— but the ingestion interface must accept them later without rewriting the Core
Agent.

## Phases (Master Prompt)

0. Research (THIS COMMIT) → 1. Caspian foundation → 2. Identity →
3. Database+memory → 4. Timetable → 5. Email → 6. PDF → 7. Core agent →
8. Proactive → 9. Frontend → 10. End-to-end.

Phase 1 is **not started**. It begins only after explicit confirmation of the
Phase 0 proposal in `docs/01-architecture.md` (which ends with the minimal
`Hello CampusOps` flow to verify).

## Repo layout (proposed, not yet created)

See `docs/01-architecture.md` § Project structure. Key constraint from the
official Caspian guide: **never create a `caspian/__init__.py` package** — it
shadows the installed `caspian` SDK. Our adapter will live at
`backend/app/comms/` (not `backend/app/caspian/`).

## Configuration

Copy `.env.example` to `.env` when Phase 1 starts. No secrets are committed.
