# CampusOps Phase 0 — Caspian-first architecture proposal

Status: **PROPOSAL — awaiting confirmation. No implementation yet.**
Companion: `docs/00-caspian-capability-map.md` (verified SDK facts).

## 1. Technology choices

- **Backend:** Python 3.14 (local) / 3.12+ baseline, FastAPI, Pydantic v2,
  SQLAlchemy 2.0, Alembic. Scheduler: APScheduler (daily brief, deadline
  sweeps) in backends worker process. HTTP: `httpx` (already a Caspian dep).
- **Comms:** `caspian-sdk==1.0.2` (pinned; v1 `Caspian` API only, legacy
  `CommClient` forbidden). Auth via `CASPIAN_API_KEY`/`CASPIAN_BASE_URL`.
- **DB:** PostgreSQL 16 + `pgvector` (structured tables = source of truth;
  embeddings for PDF/email semantic memory). SQLite only for throwaway local
  spikes, never committed as the design target.
- **AI/LLM:** provider-agnostic `ask()` seam (OpenAI-compatible endpoint,
  `OPENAI_BASE_URL` switchable) behind the Core Agent's tool loop. No chain-
  of-thought leaves the server. Model key in env only.
- **Frontend (Phase 9):** Next.js + TypeScript + Tailwind + shadcn/ui.
- **Tests:** pytest + pytest-asyncio; Caspian `cx.interpret()` /
  `cx.app.rules` for offline handler tests, `POST /v1/test-emails` for live
  verify. **Infra:** docker-compose (api, worker, db+pgvector, web), `.env.example`,
  health checks, seed scripts.

## 2. Caspian-first message lifecycle

```text
STUDENT ──(email/telegram/…)──▶ gateway/platform ──▶ Caspian SDK
  (verify → parse → normalize to Thread/Message) ──▶ CampusOps handler
  ──▶ resolve student (msg.sender+thread) ──▶ Core Agent (tools+memory+LLM)
  ──▶ decision ──▶ thread.post/send_blocks (same Thread) ──▶ Caspian dispatch
  ──▶ STUDENT.   Proactive path: scheduler/event ──▶ Core Agent ──▶
  persisted thread_id + thread.send/initiate/schedule ──▶ STUDENT.
```

Rules: one `@cx.on_message` handler for all channels; `thread.post` for
replies, `thread.send`/`initiate`/`schedule` for proactive; `send_blocks` for
rich content with text fallback; `ack` + `overlap="queue"` so slow LLM turns
don't interleave; `ctx.skipped` logged. Web + Caspian share ONE Core Agent
(`backend/app/agents/core.py::handle_turn()`); the web route and the Caspian
handler are both thin callers of it.

## 3. Authentication model

- Caspian: `CASPIAN_API_KEY` (dashboard/`caspian init project`/device-auth/
  sandbox) + `CASPIAN_BASE_URL`; per-channel tokens (`TELEGRAM_BOT_TOKEN`,
  Slack/Discord OAuth) as `channels.add()` kwargs from env. Webhook secrets
  verified by the SDK.
- Students: app-level auth (Phase 2; e.g. JWT/session) bound to `students`
  row; Caspian `msg.sender` allowlist (`CASPIAN_ALLOWED_SENDERS`) as a guard
  rail for tool-wielding turns. College Gmail via OAuth (read-only Gmail API),
  **never passwords** — Caspian email is the agent's own address, a separate
  concern from ingesting the student's college mailbox.
- Isolation: every student-scoped row carries `student_id`; all queries filter
  by it; Caspian identity resolution is the only bridge, and it is explicit
  and logged. Webhook endpoints verify signatures before any logic runs.

## 4. Communication abstraction (wraps the REAL SDK)

`backend/app/comms/` — NOT named `caspian/` (official guide: a local
`caspian/__init__.py` shadows the installed SDK):

```text
backend/app/comms/
  client.py        # builds Caspian(api_key=…), channels.add("email", username=…); exposes cx
  handlers.py      # single @cx.on_message + @cx.on_action; calls agents.core.handle_turn
  service.py       # CommunicationService: reply/proactive/rich/history over real Thread
  identity.py      # msg.sender+thread → student_id mapping + allowlist
  gateway.py       # FastAPI routes → cx.handle("gateway"|channel, body, headers)
 _runner.py        # cx.run() entrypoint (hosted poll loop process)
```

Conceptual surface (names adapt to the SDK, never fight it):

- `handle_inbound(thread, msg, ctx)` — resolve student, call Core Agent.
- `reply(thread, text)` → `thread.post(text)` (+ `stream()` for long answers).
- `send_proactive(thread_id, text)` → `Thread(thread_id).send/initiate/schedule`.
- `conversation_context(thread_id)` → `thread.history()` + DB `conversations/messages`.
- `send_rich(thread, blocks, fallback_text)` → `thread.send_blocks(...)`.

No business file imports `caspian` directly except `comms/`; no
`if channel ==` outside `comms/`.

## 5. Core Agent + memory + ingestion (V1)

- `backend/app/agents/core.py` — tool-using loop. Tools (Phase 7):
  `get_student_profile/update_student_profile`, `get_today/tomorrow/week/
  next_class`, `get_upcoming_deadlines/exams`, `search_emails`,
  `get_important_updates`, `search_documents/search_memory`, task/reminder
  CRUD, `generate_daily_plan`. Retrieval-first: profile → timetable →
  deadlines → recent important emails → exams → memory, then reason.
- Layered memory (no giant `memory.md`): Postgres tables
  (`students, student_preferences, courses, timetable_entries, emails,
  email_extractions, documents, document_chunks, announcements, deadlines,
  exams, tasks, reminders, notifications, memories, conversations, messages,
  integrations`) with `student_id, source, type, timestamp,
  confidence, status/version`; pgvector embeddings for chunks/extractions.
- Ingestion: `InformationSource` interface → `EmailSource` (Gmail API),
  `PdfSource` (upload), `TimetableSource` (upload/manual) → Normalizer →
  Extractor (classification: announcement/assignment/deadline/exam/timetable
  or room change/event/placement/notice/irrelevant + structured facts with
  source+timestamp) → Relevance Engine (profile-aware: applies to THIS
  student?) → Memory. `MoodleSource`/`WhatsAppSource` later implement the same
  interface; Core Agent untouched. Email/PDF text is UNTRUSTED — never overrides
  system instructions; uploads validated + size-limited; PII redacted in logs.
- Change/conflict detection: extractions carry source+timestamp; conflicting
  official facts coexist with provenance, surfaced to the student, never
  silently overwritten; schedule changes trigger proactive notify on relevance.

## 6. Proactive + daily brief

APScheduler jobs (morning brief, deadline sweep, important-change fan-out):
load student → gather (today/tomorrow, deadlines, important updates) →
`handle_turn(kind="proactive")` → relevance/spam gate (priority, quiet hours,
dedupe) → `send_proactive` via Caspian. Example brief shape (content via
retrieved facts only, never hallucinated):

```text
GOOD MORNING 👋  Today's classes: …  Upcoming: …  Important: …
Priority: 1. … 2. …
```

## 7. Project structure (to be created in Phase 1+)

```text
campus_os/
  README.md  .env.example  .gitignore  docker-compose.yml
  docs/ 00-caspian-capability-map.md  01-architecture.md
  backend/
    app/
      main.py  config.py
      api/          # student, timetable, email, documents, deadlines, tasks, notifications, chat, integrations (+ openapi)
      agents/       # core.py (ONE agent), tools/
      comms/        # client/handlers/service/identity/gateway/_runner (Caspian adapter; note name)
      ingestion/    # base.py + email.py + pdf.py + timetable.py (+ moodle.py/whatsapp.py later)
      memory/       # models, store, embeddings, retrieval
      models/ db/   # sqlalchemy models, session, migrations (alembic)
      services/ jobs/  # brief, reminders, change detection
    tests/          # unit + integration + e2e (incl. cx.interpret() handler tests, isolation tests)
    requirements.txt  Dockerfile
  frontend/         # Phase 9: landing, auth, onboarding, dashboard, chat, timetable, email, docs, tasks, notifications, profile, settings
  scripts/seed_demo.py  # fictional student + timetable + emails + deadlines + docs, labeled demo
```

## 8. Integration plan (phases gated on verification)

- P1 Caspian foundation: `comms/` + `gateway.py` + `_runner.py` + offline
  `interpret()` test + live `POST /v1/test-emails` verify (needs
  `CASPIAN_API_KEY`, operator-chosen email `username`).
- P2 Identity: onboarding (conversational via Caspian + web UI), sender→student
  map, isolation tests.
- P3 DB+memory (Postgres+pgvector, migrations, retrieval service).
- P4 Timetable (CRUD + views + agent tools). P5 Email (Gmail OAuth + pipeline).
  P6 PDF (extract→chunk→facts+embeddings). P7 Core Agent wiring. P8 Proactive
  jobs. P9 Frontend (same agent endpoint). P10 Full e2e incl.
  Email/PDF→Memory→Agent→Caspian loop + demo seed + compose.

## 9. First minimal Caspian flow (Phase 1 acceptance, NOT yet implemented)

```python
# backend/app/comms/_runner.py (PLAN — Phase 1 will create this)
import os
from caspian import Caspian
cx = Caspian(api_key=os.environ["CASPIAN_API_KEY"])  # SDK reads nothing itself
cx.channels.add("email", username=os.environ["CAMPUSOPS_MAILBOX"])  # ask operator first

@cx.on_message({"overlap": "queue"})
def handle(thread, msg, ctx):
    if msg.text.strip().lower() == "hello campusops":
        thread.post("Hello! I'm CampusOps, your personal academic agent.")
    else:
        thread.post("…")  # Phase 7 replaces with agents.core.handle_turn()

if __name__ == "__main__":
    cx.run()
```

Verify: `POST /v1/test-emails {"text":"Hello CampusOps"}` →
`GET /v1/events?type=message.sent` shows the reply; then a real email to the
printed agent address. Offline: `cx.interpret()` unit test asserting the reply
without network.

## 10. Open questions for confirmation

1. Phase-1 channel: hosted **email** (recommended, zero credential) — confirm,
   and provide the desired mailbox `username` when Phase 1 starts?
2. Approve `backend/app/comms/` naming + FastAPI+Postgres+pgvector baseline
   (Python 3.12+)? Frontend deferred to Phase 9 as planned?
3. May Phase 1 create the backend skeleton + `comms/` + offline test (needs
   `CASPIAN_API_KEY` only at run time, never committed)?
