# CampusOps — project report

Date: 2026-09-12 · Status: **fully functional, verified end to end.**

## 1. What it is

CampusOps is a personal academic agent for students. One Core Agent brain
serves web chat, Telegram, and email: it tracks timetables, deadlines, exams,
college email, and documents, answers questions, and notifies proactively
(morning brief, due-soon deadlines, reminders, room-change and class-start alerts).

## 2. Verification summary (this audit)

| Layer | Result |
|---|---|
| Backend tests | **62/62 pass** (isolated SQLite, deterministic LLM, ~15s) |
| Frontend typecheck | `tsc --noEmit` clean |
| Frontend build | `next build`, 17/17 pages |
| Live API audit | **43/43 checks** (auth, onboarding, timetable CRUD/scope/upload/from-text, email, documents+rescan+search, planner, chat intents, notifications, prefs, integrations, system, profile) |
| Live web audit | **15/15 pages return 200** |
| Telegram surface | `getMe @Sankiyy_bot` ✓, `/` menu 10/10 commands ✓ |
| Caspian loop | verified earlier: test mail in → `message.received` → runner → `message.sent` |

Total: **120+ checks green.** Failing-test policy: suite runs offline-safe
(`DevLLM` pinned in `conftest.py`); live-model quality is verified separately.

## 3. Feature inventory (all working)

- **Auth**: register/login/JWT, Google sign-in (auto-create + onboarding), per-student isolation (cross-student access → 404).
- **Onboarding**: 8-step conversational setup (web + any chat channel), duplicate PRN/email guards, progress UI.
- **Core Agent**: model-first replies (user card + targeted facts + 6-turn history), small-talk one-liners, reminder/task creation, hide/show/delete timetable by chat, reminder listing, DevLLM fallback on provider errors.
- **Timetable**: CRUD, CSV/JSON upload (flexible headers), paste-text, PDF/photo scan with batch-cell splitting + OCR retry, `scope=mine|all`, frontend My-classes toggle with Div/Batch badges.
- **Email**: Gmail OAuth (signed state, browser callback), sync with window params, 401 auto-refresh, 10-kind classification, date/room/subject extraction, relevance filter, auto deadlines/exams/announcements, change detection.
- **Documents**: PDF/TXT/CSV/XLSX/DOCX/PNG/JPG, layout extraction, garbage detection, vision-OCR fallback + Re-scan button, hybrid search (embedding + keywords), per-item deadline/exam creation.
- **Planner**: deadlines/tasks/reminders/exams CRUD + done-flows, urgency badges, `/planner/focus` ranked answer.
- **Notifications**: kinds toggles, quiet hours (midnight wrap), channel choice, gateway-first + Telegram-fallback delivery, queued/sent/failed/suppressed states, class-start (~15 min) + exam (48h) sweeps.
- **Telegram**: first-time guide, 9 slash commands + live `/` menu, 4-button keyboard, compact formatted answers, chat-id capture for proactive delivery.
- **System**: `/api/system/status` connection board, `/api/system/help` guide, `/health`, OpenAPI `/docs`.
- **Frontend**: 15 pages (landing with Telegram phone spotlight + GitHub button + project footer, auth, onboarding, dashboard, chat, timetable, email, documents, planner, notifications+preferences, profile, settings, help).

## 4. Known limits (honest)

- OpenRouter free tier: 50 req/day shared (model + vision OCR). App degrades to facts composer, never errors.
- `api.trycaspianai.com` TLS is blocked from some networks (revocation check); Telegram Bot API is the working fallback there.
- Scanned PDFs need vision quota; image-only uploads need an OCR engine or the vision path.
- Gmail refresh tokens live in `integrations` — use a vault/KMS before real student data.
- Semantic recall is portable hash embeddings + cosine (pgvector path documented, not yet cut over).
- Moodle/WhatsApp: designed as future `InformationSource` plugins, not built.

## 5. Run it

```powershell
python -m scripts.init_db --seed
python -m uvicorn backend.app.main:app --port 8000      # :8000
cd frontend; npm run build; npm run start -- -p 3001    # :3001
python -m backend.app.jobs.worker                        # scheduler
$env:TELEGRAM_SELF_HOST="1"; python -m backend.app.comms.runner   # ONE bot runner
```

Sample login `demo.student@example.com` / `demo1234`. Full credential +
console setup: [`DEPLOYMENT.md`](DEPLOYMENT.md). Per-area docs: `BACKEND.md`,
`FRONTEND.md`, `API.md`, `ERROR_HANDLING.md`, `AGENT.md`, `USER_GUIDE.md`,
`USER_CARD_SPEC.md`, `FEATURES.md`.
