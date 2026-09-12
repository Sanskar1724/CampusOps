# API reference

Base `http://localhost:8000`. Interactive docs at `/docs` (OpenAPI).
Auth: `Authorization: Bearer <JWT>` on everything except `/health`,
`/api/auth/*`, `/caspian/gateway`, `GET /api/integrations/gmail/callback`.

| Method & path | Purpose |
|---|---|
| `POST /api/auth/register` | Create account (full profile → done, else pending) → token |
| `POST /api/auth/login` | Email + password → token |
| `GET /api/auth/me` | Current profile |
| `GET /api/auth/google/url?redirect_uri=` | Start Google sign-in |
| `POST /api/auth/google/callback` | `{code, redirect_uri}` → token (creates account if new) |
| `GET/PATCH /api/student/profile` | Profile |
| `POST /api/student/onboarding` | `{text}` → next onboarding reply |
| `GET/POST /api/student/memories` | Long-term memory entries |
| `GET/PUT /api/student/preferences` | Notify toggles, quiet hours, channel, hidden subjects/days |
| `GET/POST /api/timetable/` `PUT/DELETE /api/timetable/{id}` | Timetable CRUD (`GET ?scope=mine\|all`) |
| `POST /api/timetable/upload` | CSV/JSON replace |
| `POST /api/timetable/from-text` | `{text}` paste → rows |
| `POST /api/timetable/from-document` | PDF/photo scan → rows + method + preview |
| `GET /api/email/` `/api/email/important` | Mail + classifications |
| `POST /api/email/sync?days=&limit=` | Gmail pull (auto token refresh) |
| `GET/POST /api/documents/` `DELETE /api/documents/{id}` | Docs CRUD |
| `POST /api/documents/upload` | PDF/TXT/CSV/XLSX/DOCX/PNG/JPG → facts + `extraction` method |
| `POST /api/documents/{id}/rescan` | Re-upload → vision-OCR retry, rebuild chunks |
| `GET /api/documents/search?q=` | Hybrid semantic search |
| `GET/POST /api/planner/deadlines` `POST /api/planner/deadlines/{id}/done` | Deadlines |
| `GET/POST /api/planner/tasks` `POST /api/planner/tasks/{id}/done` | Tasks |
| `GET/POST /api/planner/reminders` | Reminders |
| `GET /api/planner/exams` | Exams |
| `GET /api/planner/focus` | Ranked do-now answer |
| `GET /api/notifications/` | Alert feed (incl. delivery `status`/`error`) |
| `POST /api/chat/` | `{text}` → `{reply}` (same Core Agent as Caspian) |
| `GET /api/integrations/` | Connected providers |
| `GET /api/integrations/gmail/auth-url` | Signed OAuth URL (per-student state) |
| `GET /api/integrations/gmail/callback` | Google redirect target (no login needed) |
| `POST /api/integrations/gmail/callback` | Manual code fallback |
| `DELETE /api/integrations/gmail` | Disconnect |
| `GET /api/system/status` | Connection board (db, model, gateway, telegram, gmail) |
| `GET /api/system/help` | User guide markdown |
| `GET /health` | Liveness |
| `POST /caspian/gateway` | Hosted push receiver (503 unconfigured, 502 unreachable) |
