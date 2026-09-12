# Error handling

## HTTP contract

| Code | Meaning in CampusOps | Frontend behavior |
|---|---|---|
| 200 | OK (payload or `{id}`, `{deleted}`, `{updated}`) | render |
| 400 | Bad input (validation message in `detail`) | show `detail` text, no crash |
| 401 | Missing/bad token | clear token → redirect `/login` ("Session expired") |
| 404 | Not found **or not yours** (isolation returns 404, never 403, to avoid leaking existence) | "not found" state |
| 409 | Conflict: PRN/email taken, Gmail not connected/expired | contextual guidance |
| 502 | Upstream failed (Gmail API, gateway unreachable) | show message + retry action |
| 503 | Messaging not configured (no Caspian key) | setup hint |

Validation errors from Pydantic return 422 with field details (frontend
currently surfaces the first message — see `lib/api.ts`).

## Upload limits & rules

| Endpoint | Limit | Rejections (400) |
|---|---|---|
| `/timetable/upload` | 2 MB, CSV/JSON only | bad headers, unknown days, bad times |
| `/timetable/from-document` | PDF 15 MB, image 5 MB | unreadable file, no weekday+time rows (shows seen-text preview) |
| `/documents/upload` | PDF 15 MB, image 5 MB, office 5 MB | unsupported type, empty text, scanned-without-OCR |
| chat text | 4000 chars logged | longer input truncated in logs only |

Scanned PDFs: text-layer → garbage check → vision OCR retry → `ocr-failed`
stays queryable with an amber warning + Re-scan button. Garbage chunks
(score > 0.5) are never embedded or searched.

## Delivery states (`notifications.status`)

`queued` (waiting/config missing) → `sent` (+`sent_at`) → terminal.
`failed` (+`error`, body untouched) retries on later sweeps.
`suppressed` (kind disabled in prefs) never retries.

## Known failure modes → fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Session expired` loop | Old token (secret rotated) or wrong password | log in again / reset password |
| Gmail 401 on sync | Access token >1h old | automatic refresh; if revoked → reconnect |
| `redirect_uri_mismatch` | URI missing in Google Console | register both URIs (see DEPLOYMENT.md) |
| Telegram bot silent | webhook claimed elsewhere / two pollers | one `TELEGRAM_SELF_HOST=1` runner; it clears webhooks on start |
| Gateway TLS errors | network blocks `api.trycaspianai.com` | Telegram Bot-API fallback covers delivery; hotspot for hosted |
| `Unknown day` on upload | exotic day label | Mon–Sun / 0–6 / full names supported; else fix the header |
| Empty chat answers | free-model 429 | ResilientLLM serves retrieved facts; quota resets / add credits |

## Logs

Backend logs to stdout (uvicorn). Handler exceptions print tracebacks but still
reply gracefully. Never log: passwords, tokens, email bodies, PDF text.
