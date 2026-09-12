# Backend — FastAPI service

Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic v2. Pinned deps: `backend/requirements.txt`.

## Layout

```text
backend/app/
  main.py          # FastAPI app, CORS, lifespan (init_db), router wiring
  config.py        # env (CASPIAN_*, GMAIL_*, APP_SECRET_KEY); SDK never reads .env itself
  db.py            # engine/session; init_db() + ensure_columns() lightweight migration
  models.py        # 17 tables; every student row carries student_id
  schemas.py       # Pydantic request/response models
  security.py      # PBKDF2 passwords, JWT sessions, OAuth state signer
  llm.py           # OpenAICompatibleLLM → ResilientLLM → DevLLM fallback chain
  embeddings.py    # portable token-hash vectors + cosine
  user_guide.py    # USER_GUIDE.md loader + compact agent pointer block
  api/
    auth.py        # register / login / me / Google sign-in
    resources.py   # student, timetable, email, documents, planner, notifications, chat, integrations
    system.py      # /api/system/status board + /api/system/help guide
    deps.py        # ⭐ user-orientation router key: get_user_context() + prefs + quiet hours
  agents/
    core.py        # handle_turn() — one brain for web + Caspian + jobs
    tools.py       # schedule/deadline/exam/email/doc/task/reminder/plan/focus tools
    onboarding.py  # 8-step conversational onboarding state machine
  comms/
    client.py      # build_caspian_app() — hosted email / telegram self-host / offline
    handlers.py    # single on_message + on_action (buttons), identity, first-time guide
    service.py     # thread.post wrapper, /commands, quick-action buttons, reply formatting
    proactive.py   # gateway-first, Telegram-fallback delivery with statuses
    runner.py      # cx.run() (hosted) / cx.poll("telegram") (self-host)
  ingestion/
    base.py        # InformationSource protocol (Moodle/WhatsApp plug in here later)
    email_source.py# Gmail REST fetch, OAuth helpers, token refresh, classify→extract→relevance
    pdf_source.py  # PDF/TXT/CSV/XLSX/DOCX/image extraction + vision-OCR fallback
    extract.py     # classifier, fact/date/room/subject scan, garbage detector
    timetable_source.py # CSV/JSON upload, timetable-from-text, batch-cell splitting
  memory/          # structured save + hybrid semantic search (embedding + keywords)
  jobs/            # daily brief, deadline/reminder sweeps, delivery retry + worker entry
```

## Run

```powershell
python -m uvicorn backend.app.main:app --port 8000   # API + /docs
python -m backend.app.jobs.worker                     # scheduler loop
python -m backend.app.comms.runner                    # hosted Caspian poll
$env:TELEGRAM_SELF_HOST="1"; python -m backend.app.comms.runner   # Telegram poll
python -m scripts.init_db --seed                      # tables + demo data
```

## Database & migrations

- Local default `sqlite:///./campusops.db`; production `DATABASE_URL=postgresql+psycopg2://…`.
- No Alembic: `init_db()` runs `create_all` + `ensure_columns()`, which `ALTER TABLE`s
  newly added columns onto existing databases (SQLite + Postgres). New column?
  Add it to the model **and** to `ensure_columns()`.

## Auth model

JWT (`APP_SECRET_KEY`, 7-day expiry) → `get_current_student()` → **every query
filters by that student id**. Caspian `msg.sender` maps to `caspian_sender`;
Google sign-in matches `college_email`. Passwords: PBKDF2-HMAC-SHA256, 200k rounds.
