# Frontend — Next.js 14 + Tailwind

App Router, TypeScript strict, no component library (Tailwind utilities +
shared `.card/.btn/.input` classes in `app/globals.css`).

## Pages (`frontend/app/`)

| Route | Page |
|---|---|
| `/` | Landing (features, stats, quick start) |
| `/login`, `/register` | Password auth + Continue with Google |
| `/auth/google/callback` | OAuth code → token exchange landing |
| `/onboarding` | 8-step conversational setup with progress bar |
| `/dashboard` | Gradient greeting, stat cards, brief, quick actions |
| `/chat` | Agent chat, suggested prompts, auto-scroll |
| `/timetable` | My-classes / whole-class toggle, form, CSV/JSON + PDF/photo scan + paste |
| `/email` | Classified important mail + fact pills + Gmail sync |
| `/documents` | Multi-format upload, OCR status, re-scan, semantic search |
| `/tasks` | Deadlines (urgency badges), exams, tasks, reminders |
| `/notifications` | Alert feed + preferences (kinds, quiet hours, channel) |
| `/profile` | Avatar header + editable profile |
| `/settings` | Backend connection board + Gmail connect |
| `/help` | User guide served from the backend (single source) |

Shared: `components/Shell.tsx` (sidebar + mobile pill nav), `lib/api.ts`
(JWT storage, 401 → login redirect, JSON error parsing, file upload helper).

## Run

```powershell
cd frontend
npm install
npm run dev        # :3001 with hot reload
npm run build; npm run start -- -p 3001   # production
npx tsc --noEmit   # typecheck
```

Env: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
Backend CORS allows `localhost:3000` and `localhost:3001`.

## Conventions

- Client components (`"use client"`) fetch in `useEffect`; server renders static shells.
- Never hardcode the API host — always `lib/api.ts`.
- Errors: parse `err.message` as JSON and show `detail` (see ERROR_HANDLING.md).
- Emoji are UI affordances (nav, badges, empty states) — keep them in `page.tsx`,
  never in shared logic.
