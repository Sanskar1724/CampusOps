# Deployment

## Environments

| | Local dev | Docker (production-like) |
|---|---|---|
| DB | SQLite `./campusops.db` | Postgres 16 + pgvector (`db` service) |
| API | `uvicorn … --port 8000` | `api` service :8000 |
| Web | `npm run dev` :3001 | `web` service :3001 |
| Worker | `jobs.worker` loop | `worker` service |
| Caspian | `comms.runner` / self-host poll | `caspian` service |

```powershell
docker compose up --build -d
docker compose logs -f api
```

`backend/Dockerfile` runs `init_db` on boot; `worker/Dockerfile` and
`web/Dockerfile` are separate images (see `docker-compose.yml`).

## Environment checklist (`.env`, never committed)

Required: `APP_SECRET_KEY` (long random), `DATABASE_URL` (compose sets Postgres).
AI: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL`, `VISION_MODEL` (optional).
Messaging: `CASPIAN_API_KEY`, `CASPIAN_BASE_URL`, `CAMPUSOPS_MAILBOX`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_SELF_HOST=1` (self-host mode).
Gmail: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REDIRECT_URI`.
Frontend: `NEXT_PUBLIC_API_URL` (bake time for `web` image).

## Google Console (one time)

OAuth client (Web app) Authorized redirect URIs — register **both** exactly:
`http://localhost:8000/api/integrations/gmail/callback` (replace host in prod)
`http://localhost:3001/auth/google/callback`
OAuth consent → Audience → add each student email as test user (while Testing).

## Telegram (one time)

Talk to @BotFather → `/newbot` → token → `TELEGRAM_BOT_TOKEN`.
Run exactly ONE poller (`TELEGRAM_SELF_HOST=1` runner clears webhooks on start).

## Caspian (one time)

`caspian init project` or dashboard key → `CASPIAN_API_KEY`; choose
`CAMPUSOPS_MAILBOX` (`campusops@agents.trycaspianai.com`); run the hosted
`comms.runner`. Verify: test mail → `message.received` → `message.sent`.

## Health & backup

- `GET /health`, `GET /api/system/status` (per-integration board).
- Compose `db` has a `pgdata` volume; SQLite: back up `campusops.db`.
- OpenRouter free tier: 50 req/day shared — add $10 credits for 1000/day
  (credits aren't spent on `:free` models).
