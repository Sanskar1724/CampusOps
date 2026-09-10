# Caspian foundation — what exists and how to verify it

## What was built (receive → reply through the real SDK)

- `backend/app/comms/client.py` — `build_caspian_app()` constructs
  `Caspian(api_key=…, base_url=…)` explicitly (the SDK never reads `.env`
  itself), connects hosted email with an operator-chosen `mailbox`, and
  registers the single handler. Refuses to build when the mailbox is blank
  (never mints a random address) and refuses live builds without an API key.
- `backend/app/comms/handlers.py` — one `@cx.on_message({"overlap": "queue"})`
  rule, no channel filter: the same code answers on every connected channel.
- `backend/app/comms/service.py` — `reply_text()` (`thread.post`) is the only
  send path; business logic never imports `caspian` directly.
- `backend/app/agents/core.py` — `respond_to_text()` brain seam shared by all
  future channels (Caspian chat, web chat). `"Hello CampusOps"` →
  `"Hello! I'm CampusOps, your personal academic agent."`
- `backend/app/comms/runner.py` — live hosted poll loop (`cx.run()`):
  `python -m backend.app.comms.runner`.
- `backend/app/main.py` — FastAPI with `GET /health`,
  `POST /caspian/gateway` (hosted push alternative to polling), OpenAPI docs.
- `backend/tests/test_caspian_foundation.py` — 6 offline tests, zero network
  (`dispatch=False`, real `Caspian`/`Thread`/`Message`/`MemoryInterpreter`).

Naming note: the adapter lives in `comms/`, not `caspian/`, because a local
`caspian/__init__.py` would shadow the installed SDK (official guide warning).

## Offline verification (no credentials needed)

```powershell
python -m pytest backend/tests/ -v
```

Covers: hello/fallback brain replies, handler posting the exact hello reply on
a real `Thread`, kernel routing (`interpret()` yields the `Host` command),
channel-agnostic rule (email + telegram), mailbox-required guard.

## Live verification — DONE 2026-09-10

- Gateway reachable, key valid (`GET /v1/channels` → live catalog).
- Email connected: `campusops@agents.trycaspianai.com` (`conn_3441d0…`).
- Telegram hosted also connected: `@Sankiyy_bot`.
- Test email in → `message.received`; polling `python -m backend.app.comms.runner`
  → handler ran → `message.sent` ("What is your PRN…", correct onboarding turn
  for a new sender). Full Caspian loop confirmed live.
- Note: `POST /v1/test-emails` without a target hits the newest connection
  (telegram rejects test mail) — always pass
  `{"connection_id": "conn_3441d0…"}` for email tests.
- Note: only ONE runner per inbox. Two pollers race cursors and replies go missing.
1. Set `CASPIAN_API_KEY` and `CAMPUSOPS_MAILBOX` (see `.env.example`).
2. `python -m backend.app.comms.runner` — note the printed agent address.
3. Send `Hello CampusOps` to that address; expect the hello reply.
4. Programmatic check:
   `POST https://api.trycaspianai.com/v1/test-emails {"text":"Hello CampusOps"}`
   then `GET /v1/events?type=message.sent` should show the sent reply.

## Deliberately not built yet

Student identity/onboarding, database/memory, timetable, college-email
ingestion, PDF handling, tool-using agent, scheduler/proactive sends, web UI.
Proactive helpers (`send`/`initiate`/`schedule`) are intentionally absent until
the scheduler work lands — no stubbed functionality.
