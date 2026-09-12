# Deployment — live URLs for judges (Vercel + Render, all free)

Architecture: **Vercel** hosts the Next.js frontend, **Render** hosts the
FastAPI backend + worker + free Postgres. Total cost: $0.

```text
browser ─▶ campusops-xxx.vercel.app (frontend)
               │  NEXT_PUBLIC_API_URL
               ▼
         campusops-api.onrender.com (backend+DB)
               ├── campusops-worker (briefs/reminders)
               └── campusops-db (Postgres)
```

## Step 1 — backend on Render (~10 min)

1. Push this repo to GitHub (done) and sign in at **render.com** (GitHub login).
2. **New → Blueprint** → select `Sanskar1724/CampusOps` → Apply.
   Render creates `campusops-api`, `campusops-worker`, `campusops-db`.
3. While services build, open the **campusops-api → Environment** tab and fill:
   - `OPENAI_API_KEY`, `CASPIAN_API_KEY`, `TELEGRAM_BOT_TOKEN`,
     `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` (copy from your local `.env`)
   - `APP_SECRET_KEY` is auto-generated — leave it.
4. Copy the API public URL, e.g. `https://campusops-api-xxxx.onrender.com`.
   Open `<url>/health` → expect `{"status":"ok"}`.
5. Seed demo data (judges log in with it once):
   Render → `campusops-api` → **Shell** tab, run:
   `python -m scripts.init_db --seed`
6. Enable pgvector (one time): `campusops-db` → **Connect → PSQL**, run:
   `CREATE EXTENSION IF NOT EXISTS vector;`
7. In the API service env, set `FRONTEND_URLS` to your Vercel URL (Step 2)
   and redeploy the API (Manual Deploy).

## Step 2 — frontend on Vercel (~5 min)

1. Sign in at **vercel.com** (GitHub login) → **Add New → Project** →
   Import `Sanskar1724/CampusOps`.
2. Set **Root Directory** to `frontend` (Edit button next to it).
3. Framework Preset: Next.js (auto). Build Command stays default.
4. **Environment Variables**: add
   `NEXT_PUBLIC_API_URL` = `https://campusops-api-xxxx.onrender.com`
   (your URL from Step 1 — no trailing slash).
5. Deploy. You get `https://campusops-xxx.vercel.app`.

## Step 3 — reconnect OAuth to production URLs

Google Cloud Console → your OAuth client → **Authorized redirect URIs**, add:
- `https://campusops-api-xxxx.onrender.com/api/integrations/gmail/callback`
- `https://campusops-xxx.vercel.app/auth/google/callback`

Backend env `GMAIL_REDIRECT_URI` must equal the first one exactly
(update it in Render → redeploy API). Keep test users on the consent screen.

## Step 4 — Telegram

No change needed: the self-host poller runs anywhere. Either run the worker
service command override once, or keep polling from your machine. One poller
only. Verify the `/` menu via `getMyCommands`.

## Judge checklist (paste into your submission)

- Live app: `https://campusops-xxx.vercel.app`
- API docs: `https://campusops-api-xxxx.onrender.com/docs`
- Demo login: `demo.student@example.com` / `demo1234`
- Telegram: `@Sankiyy_bot` — try `/focus`, tap the 4 buttons
- Repo: `https://github.com/Sanskar1724/CampusOps`

## Notes & limits

- Render free web services **sleep after ~15 min idle** — first judge click
  takes ~50s to wake. Mention it in your video/README.
- Render free Postgres expires after 90 days — plenty for judging; for longer,
  move to Neon/Supabase free tier (just swap `DATABASE_URL`).
- `NEXT_PUBLIC_API_URL` is baked at build time: changing it needs a Vercel
  redeploy. Same for `GMAIL_REDIRECT_URI` (API redeploy).
- Alternative single-platform path: `docker compose up --build` on any VPS
  (see `docker-compose.yml`).
