<p align="center">
  <img src="frontend/public/logo.svg" width="72" alt="CampusOps logo" />
</p>

<h1 align="center">CampusOps</h1>
<p align="center"><strong>Campus Operating System</strong> — Your personal academic agent that never misses a class, deadline, or notice.</p>

<p align="center">
  <img src="https://img.shields.io/badge/backend-FastAPI%20%C2%B7%20Python-009688" alt="backend" />
  <img src="https://img.shields.io/badge/frontend-Next.js%2014-black" alt="frontend" />
  <img src="https://img.shields.io/badge/comms-Caspian%20SDK-4F46E5" alt="comms" />
  <img src="https://img.shields.io/badge/db-Postgres%20%C2%B7%20SQLite-336791" alt="db" />
  <img src="https://img.shields.io/badge/tests-62%20passing-brightgreen" alt="tests" />
  <img src="https://img.shields.io/badge/deploy-Vercel%20%2B%20Render-000000" alt="deploy" />
</p>

<p align="center">
  <a href="https://campus-ops-chi.vercel.app/"><strong>🌐 Live Demo</strong></a> •
  <a href="https://campusops-api-dcy9.onrender.com/docs">📖 API Docs</a> •
  <a href="https://t.me/Sankiyy_bot">✈️ Telegram Bot</a> •
  <a href="https://github.com/Sanskar1724/CampusOps">💻 GitHub</a>
</p>

---

CampusOps reads your **college email, timetable, and documents** — then pings you with a morning brief, urgent alerts, and answers. One Core Agent brain serves **web chat, Telegram, and email** alike.

<p align="center"><img src="docs/images/architecture.svg" width="720" alt="CampusOps architecture" /></p>

> **Why CampusOps?** Students juggle 5+ sources daily: Gmail, portal PDFs, timetable sheets, notices, reminders. CampusOps unifies them into one chat — ask *“What should I focus on today?”* and get a ranked answer from **your** data, not hallucinated.

---

## ✨ Highlights

| Feature | What it does |
|---|---|
| 🎯 **Do now focus engine** | Ranks overdue → due <24h → high priority → next class into one actionable line |
| 🗓️ **Your timetable, your rules** | Batch-filtered (`B1` only) vs whole-class view; PDF/photo scan with batch-cell splitting; hide/mute/delete by chat |
| 📧 **Email intelligence** | Gmail sync (read-only, auto token refresh), 10-kind classification, room-change radar with source |
| 📄 **Documents that answer back** | Multiformat (PDF/TXT/CSV/XLSX/DOCX/PNG/JPG) + vision OCR + hybrid search (embedding+keywords) + Re-scan |
| 🔔 **Notifications with rules** | Per-kind toggles, quiet hours (22-7), channel choice (auto/gateway/telegram), honest statuses |
| 💬 **Telegram flagship** | 10 slash commands, 4 tap buttons, first-time tour, compact answers, class-start/exam pings |
| 🔌 **Connection board** | Every integration 🟢/🔴 with fix hint in Settings → Backend connections |
| 🧠 **Model-first agent** | User card + targeted facts + 6-turn history, resilient fallback, never repeats verbatim |

Full tour: [`docs/FEATURES.md`](docs/FEATURES.md) · User manual: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)

---

## 🧱 Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic-style `ensure_columns`, JWT (PBKDF2 200k), httpx
- **Frontend:** Next.js 14 (App Router), TypeScript strict, Tailwind CSS, no UI kit
- **Comms:** Caspian SDK 1.0.2 (one handler, every channel) + Telegram Bot API direct
- **AI:** OpenAI-compatible (OpenRouter `nex-agi/nex-n2.5-mini:free`), `VISION_MODEL` for OCR, deterministic `DevLLM` fallback
- **Data:** SQLite locally → Postgres 16 + pgvector in production (`DATABASE_URL` switch)
- **Infra:** Docker (api/worker/caspian/web + db), Render (free web + DB) + Vercel (free web)

---

## 📁 Project Structure

```text
campus_os/
├── backend/app/
│   ├── main.py          # FastAPI app, CORS, lifespan, routers
│   ├── config.py        # env (never reads .env itself, explicit)
│   ├── db.py            # engine, init_db + pgvector + ensure_columns
│   ├── models.py        # 17 tables, student_id on every row
│   ├── api/             # auth, resources (student/timetable/email/docs/planner), system
│   ├── agents/          # core.handle_turn + tools + onboarding (8 steps)
│   ├── comms/           # Caspian client/handlers/service/proactive/runner
│   ├── ingestion/       # email_source (Gmail), pdf_source (vision OCR), timetable, extract
│   ├── memory/          # hybrid search, student preferences
│   └── jobs/            # brief, deadline, class_soon, exam sweeps + worker
├── frontend/
│   ├── app/             # 15 routes: landing, auth, dashboard, chat, timetable, email...
│   ├── components/      # Shell, TelegramDemo (iPhone mock)
│   └── lib/api.ts       # JWT, 401 redirect, upload helper
├── scripts/             # init_db, seed_demo (labeled demo: demo.student@example.com / demo1234)
├── docs/                # see Documentation below
└── render.yaml / docker-compose.yml + Dockerfiles
```

---

## 🚀 Quickstart (local, no keys needed)

```powershell
# 1. Backend
python -m pip install -r backend/requirements.txt
python -m scripts.init_db --seed
python -m uvicorn backend.app.main:app --port 8000   # API + /docs at :8000

# 2. Frontend (new shell)
cd frontend; npm install; npm run dev                 # web UI at :3001

# 3. Worker (new shell, optional but recommended)
python -m backend.app.jobs.worker                     # briefs, reminders, class pings

# 4. Telegram bot (new shell, optional)
$env:TELEGRAM_SELF_HOST="1"; python -m backend.app.comms.runner  # @Sankiyy_bot
```

Sample login: `demo.student@example.com` / `demo1234` · Ports: API `:8000`, web `:3001`

> All core features work offline. Live channels need keys (see `.env.example`): `CASPIAN_API_KEY` + `CAMPUSOPS_MAILBOX` for email, `TELEGRAM_BOT_TOKEN` for the bot, Google OAuth client for Gmail + Google sign-in.

---

## 🌐 Live Deployment

**Frontend on Vercel, Backend + Worker + Postgres on Render — free tier.**

- **Live app:** https://campus-ops-chi.vercel.app/
- **API docs:** https://campusops-api-dcy9.onrender.com/docs

Full click-by-click guide (Render Blueprint, Vercel Root Directory, env checklist, OAuth redirect URIs, pgvector): [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). After deploying, fill the two URLs in this README if you fork.

*Free-tier notes:* Render web sleeps after ~15m idle (first click ~50s wake), free DB expires in 90 days — enough for judges; for longer, swap `DATABASE_URL` to Neon/Supabase.

---

## 🧠 Conversational Agent (not templates)

Every reply is composed live by the model from three inputs: a per-turn **user card** (your name, batch, today's classes, deadlines, memories — see [`docs/USER_CARD_SPEC.md`](docs/USER_CARD_SPEC.md)), only the facts the question needs, and the last 6 turns of conversation. Greetings and action confirmations answer instantly; everything else is voiced fresh each time. Small talk (`hi`, `thanks`) is instant; targeted questions (`next class`, `deadlines`) return short answers; open questions (`focus`, `brief`) return the full ranked plan.

Design: [`docs/AGENT.md`](docs/AGENT.md) · Fallback: `ResilientLLM` → `DevLLM` on 429/outage, so students always get truth.

**Telegram is flagship:** first-time guide, `/` menu (10 commands), 4 buttons under every reply, compact formatting, proactive class-start (~15m) + deadline + exam pings via same Core Agent.

---

## 📚 Documentation

| Doc | What it covers | Audience |
|---|---|---|
| [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | End-user manual: onboarding, timetable, chat, email, docs, Telegram, notifications | Students |
| [`docs/USER_CARD_SPEC.md`](docs/USER_CARD_SPEC.md) | Markdown contract for the system prompt (per-turn user card) | AI / Backend |
| [`docs/AGENT.md`](docs/AGENT.md) | Retrieve → compose → fallback pipeline, cost control | Backend / AI |
| [`docs/FEATURES.md`](docs/FEATURES.md) | Feature tour with screenshots | Everyone |
| [`docs/BACKEND.md`](docs/BACKEND.md) | Service layout, DB/migrations, auth, pgvector | Backend |
| [`docs/FRONTEND.md`](docs/FRONTEND.md) | Pages, components, conventions, build | Frontend |
| [`docs/API.md`](docs/API.md) | Every endpoint, auth, request/response | Backend / Frontend |
| [`docs/ERROR_HANDLING.md`](docs/ERROR_HANDLING.md) | HTTP codes, limits, delivery states, failure → fix table | Backend / Frontend |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Vercel + Render steps, env checklist, OAuth/Telegram/Caspian setup | DevOps |
| [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md) | Full audit: features, 62 tests, live checks, limits | Judges |
| [`docs/00-caspian-capability-map.md`](docs/00-caspian-capability-map.md) | Verified Caspian SDK 1.0.2 capabilities | Comms |
| [`docs/01-architecture.md`](docs/01-architecture.md) | Caspian-first architecture diagram & decisions | Arch |
| [`docs/caspian-foundation.md`](docs/caspian-foundation.md) | Caspian proof: receive→reply loop | Comms |
| [`CONTRIBUTORS.md`](CONTRIBUTORS.md) | Team + credits | Everyone |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | PR workflow, branch rules, checks | Contributors |

All docs are also searchable via the in-app **Help** page (`/help`).

---

## ✅ Verify (offline-safe)

```powershell
python -m pytest backend/tests/ -v   # 62 tests, no network, deterministic DevLLM
cd frontend; npx tsc --noEmit; npm run build   # typecheck + 18 pages
```

Live audit (after deploy or locally with both servers up): `python scripts/audit.py` checks 43 API + 15 web + Telegram menu.

---

## 🔒 Security & Privacy

- Every query filters by JWT student (`student_id` on every row) — cross-student access returns 404, with test proving isolation.
- Passwords: PBKDF2-HMAC-SHA256 200k rounds, salted; JWT 7-day expiry; OAuth state is signed.
- `comms/` is the only place that imports `caspian`; no `if telegram:` in business logic.
- Email/PDF text is **untrusted data** — never executed, only summarized with source.
- `.env` never committed (see `.env.example`); `APP_SECRET_KEY` is `generateValue` on Render.

---

## 🔒 Production Notes (honest limits)

- Semantic recall uses portable hash embeddings + in-Python cosine so the demo runs anywhere; swap `embeddings.embed()` for a real model and move `embedding_json` to a pgvector column for scale (compose ships `pgvector/pg16`, `db.py` auto-creates the extension).
- Gmail uses read-only OAuth with auto token refresh (401 → refresh → retry); refresh tokens live in `integrations` — put a KMS/vault in front of the DB before real student data.
- Set a long random `APP_SECRET_KEY`; never commit `.env`.
- Moodle/WhatsApp are designed as future `InformationSource` plugins, not core rewrites — see `ingestion/base.py`.

---

## ✈️ Telegram Flagship

The fastest way to feel CampusOps: message **[@Sankiyy_bot](https://t.me/Sankiyy_bot)**. The landing page shows a live iPhone mock cycling 3 real exchanges.

- ⌨️ **10 slash commands** — type `/` for today, tomorrow, week, next, deadlines, exams, reminders, brief, focus, link, help
- 👆 **4 tap buttons** under every reply (Today · Next · Deadlines · Focus) + Markdown-stripped compact formatting
- 💬 **Short personal answers** voiced live from your user card + 6-turn history
- 🔔 **Proactive pings** — class-start (~15 min), deadline, exam, and room-change alerts via same worker
- 🔗 **Link code** — web Profile → Generate code → send `/link 123456` on Telegram to sync an existing account

One runner only: `TELEGRAM_SELF_HOST=1 python -m backend.app.comms.runner` (clears webhooks, publishes `/` menu on start). In production, the Render single service runs API + worker + Telegram together (free tier).

---

## 👥 Team

- **Sanskar** — owner · [GitHub](https://github.com/Sanskar1724)
- **Pratiksha** — contributor · [GitHub](https://github.com/Pratiksha2968)

Full credits: [CONTRIBUTORS.md](CONTRIBUTORS.md) · Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md) · License: [LICENSE](LICENSE)

---

## 📸 Screenshots

| Page | What to capture |
|---|---|
| Landing | Hero + stats + Telegram iPhone + footer |
| Dashboard | Greeting + brief + urgency badges |
| Chat | `What should I focus on today?` → ranked answer |
| Timetable | My classes (B1) vs whole-class toggle, batch badges |
| Email | Important & relevant pills + Gmail sync |
| Documents | PDF upload → facts + hybrid search |
| Telegram | `/` menu + 4 buttons + document ingestion `✅ Got file` |

> Tip: Use the sample account for all screenshots so judges can replicate.

