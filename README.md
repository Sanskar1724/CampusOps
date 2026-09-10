# CampusOps — Personal Academic Agent for Students

An AI agent that knows your academic life and proactively helps manage it —
college email, timetable, and documents in; briefs, reminders, and answers out.
**Caspian is the communication foundation**: one Core Agent serves Caspian
messaging, web chat, and scheduled nudges.

```text
STUDENT ─▶ CASPIAN SDK ─▶ comms/ ─▶ Core Agent ─┬─ memory (Postgres/SQLite + embeddings)
                                                ├─ tools (timetable, email, docs, tasks)
                                                └─ LLM (OpenAI-compatible, offline fallback)
        ◀── thread.post / gateway ── decision ──┘
```

## Quickstart (local, no credentials needed)

```powershell
python -m scripts.init_db --seed
python -m uvicorn backend.app.main:app --port 8000   # API + docs at /docs
python -m backend.app.jobs.worker                     # briefs + reminders (separate shell)
cd frontend; npm install; npm run dev                 # web UI on :3001
```

Demo login: `demo.student@example.com` / `demo1234` (seeded timetable, emails,
deadlines, room-change notice, document). Ports: API `:8000`, web `:3001`.
Sign-in options: password or **Continue with Google** (needs the same Google
OAuth client as Gmail sync, plus redirect URI
`http://localhost:3001/auth/google/callback` in its authorized list).

Live messaging needs `CASPIAN_API_KEY` + `CAMPUSOPS_MAILBOX` (see
`.env.example`), then `python -m backend.app.comms.runner` and message the
agent address. Without a key, everything else still works offline.

## Layout

- `backend/app/comms/` — Caspian adapter (client, handlers, proactive gateway
  sends, runner). Only place that imports `caspian`.
- `backend/app/agents/` — Core Agent (`core.handle_turn`), toolset (`tools`),
  conversational onboarding.
- `backend/app/ingestion/` — source interface + Gmail, PDF, timetable
  pipelines; rule-based classify/extract with optional LLM enrichment.
- `backend/app/memory/`, `models.py`, `db.py` — layered memory + schema
  (SQLite locally, PostgreSQL via `DATABASE_URL`).
- `backend/app/jobs/` — daily brief, deadline/reminder sweeps, delivery retry
  + worker entrypoint.
- `backend/app/api/` — auth (JWT), student, timetable, email, documents,
  planner, notifications, chat, integrations. OpenAPI at `/docs`.
- `frontend/` — Next.js 14 + Tailwind: landing, auth, onboarding, dashboard,
  chat, timetable, email, documents, planner, notifications, profile, settings.
- `scripts/` — `init_db`, `seed_demo` (labeled demo data).

## Verify

```powershell
python -m pytest backend/tests/ -v   # 22 offline tests, zero network
cd frontend; npx tsc --noEmit; npm run build
```

## Production notes (honest limits)

- Semantic recall uses portable hash embeddings + in-Python cosine search so
  the demo runs anywhere; swap `embeddings.embed()` for a real model and move
  `embedding_json` to a pgvector column for scale (compose already ships
  `pgvector/pg16`).
- Gmail uses read-only OAuth; refresh tokens live in `integrations` — put a
  KMS/vault in front of the DB before real student data.
- Set a long random `APP_SECRET_KEY`; never commit `.env`.
- Moodle/WhatsApp are new `InformationSource` implementations, not core rewrites.
