# CampusOps Phase 0 — Caspian Capability Map (VERIFIED, not assumed)

Date: 2026-09-09. Source of truth: installed `caspian-sdk==1.0.2`
(Python 3.14), `https://api.trycaspianai.com/SKILL.md`,
`https://api.trycaspianai.com/SKILL/plain-python.md`, PyPI page, and
`TryCaspian/caspian-sdk` README. Every item below was read from SDK source
or official docs — nothing invented.

> Legacy warning: `from caspian_sdk import CommClient` +
> `connect_*()` / `message.reply()` / `client.listen()` is the **0.6.x legacy
> API**. Current API is `from caspian import Caspian` (v1.0+). CampusOps uses
> v1 only.

## 1. Installation

- `pip install caspian-sdk` (Python 3.10+). Deps: `httpx`, `pydantic` only.
- TypeScript equivalent: `npm install caspian-sdk` (not used by CampusOps).
- CLI (separate tool): `caspian init project` (browser sign-in, writes
  `./.env`), `caspian login` (writes `~/.caspian/.env`),
  `caspian channels add <channel>`.
- Optional socket extras: `caspian-sdk[discord]`, `caspian-sdk[slack-socket]`
  (need `websockets`).
- Verified: `pip show -f caspian-sdk` → package dir `caspian/` with
  `facade/`, `catalog.py`, `core/`, `hosted/`, `adapters/`,
  `interpreters/`, `tools/`.

## 2. Client initialization

```python
from caspian import Caspian
cx = Caspian(api_key=os.environ["CASPIAN_API_KEY"],
             base_url=os.environ.get("CASPIAN_BASE_URL",
                                     "https://api.trycaspianai.com"))
```

- `Caspian(*, api_key="", base_url="", webhook_secret="",
  gateway_client=None, transport=None, dispatch=True)`.
- **Does NOT read `.env` by itself** — caller must pass `api_key`
  explicitly (official SKILL.md states this).
- `Caspian()` with no key = self-host mode only (own platform tokens).
- Gateway default: `https://api.trycaspianai.com`.

## 3. Authentication / configuration

- Hosted auth = `CASPIAN_API_KEY` (+ `CASPIAN_BASE_URL`) from
  dashboard / `caspian init project` / device-auth flow
  (`POST /v1/auth/device/start` → show `verification_uri_complete` → poll
  `POST /v1/auth/device/token`) / sandbox key
  (`POST /v1/projects/sandbox`).
- Low credit surfaces as HTTP **402** → `GET /v1/billing`, dashboard
  `https://dashboard.trycaspianai.com`, `PUT /v1/billing/autopay`.
- Secrets live in `.env`, never in code. Per-channel tokens (below) are
  passed as `channels.add()` kwargs, never committed.

## 4. Supported channels

`cx.channels.add(channel, *, via="hosted"|"self-host", display_name="",
bot_token="", webhook_url="", inbound=True, webhook_secret="",
signing_secret="", app_secret="", api_key="", **kwargs) -> Connection`.

Self-hostable catalog rows (verified in `caspian/catalog.py::CHANNELS`):
`telegram, slack, discord, email, whatsapp, messenger, sms, voice,
imessage, x, linear`. Hosted-only names the gateway may additionally serve
(e.g. `bluesky`, `instagram`) are open strings — **discover live set via**
`GET /v1/channels` with the API key; never invent a connect call.

| Channel | Inbound | Bot token rule | Notes for CampusOps |
|---|---|---|---|
| email | webhook (gateway) | not needed hosted | **Phase-1 channel.** ASK `username` first: `channels.add("email", username="<choice>")` → `<choice>@agents.trycaspianai.com`. Bare add mints random local-part. 409 returns `suggestions`. `display_name` optional. |
| telegram | webhook or poll | ALWAYS (BotFather), hosted or self-host | Needs user-supplied token. Phase 1 alt if email blocked. Self-host without public URL: `cx.poll("telegram")`. |
| discord | socket only | self-host only | `cx.listen("discord")` + extra. Hosted = OAuth via `display_name` + `authorize_url`. |
| slack | webhook or socket | self-host only | `cx.listen("slack")` (Socket Mode, `app_token`) or webhook (`signing_secret`). Hosted = OAuth. |
| whatsapp/messenger/sms/voice/imessage/x/linear | webhook | self-host only (own creds) | Hosted via gateway one-click/credit. **V1 OUT OF SCOPE** (WhatsApp explicitly deferred). |

`channels.add` is **idempotent** for an already-active hosted connection.

## 5. Message receiving

```python
@cx.on_message({"channel": "email", "overlap": "queue",
                "ack": "On it, one moment..."})
def handle(thread, msg, ctx):
    ...
```

- One handler answers every channel; adding a channel never adds handler code.
- `OnMessageOptions`: `channel` (name or list), `kind` (`dm`/`group`/`channel`),
  `command` (`/help`, `/help@Bot`), `overlap`
  (`queue`/`debounce`/`drop`/`parallel`/`stream`), `bound` (default 16),
  `ack` (instant reply pre-handler; for email/SMS/X with no typing indicator).
- `@cx.on_action({"channel": ..., "data": ..., ...})` handles button/callback
  presses. `cx.use(rule)` raw-rule escape hatch.
- `cx.app.rules` exposes the program as inspectable data.

## 6. Message object / schema

`caspian.core.types.Message` (frozen pydantic model):

- `kind="message"`, `thread_id: ThreadId`, `text: str`,
  `chat_kind: ChatKind`, `sender: str = ""`, `message_id: str = ""`,
  `attachments: tuple[Attachment, ...]`, `blocks: tuple[Block, ...]`,
  `reply_to: str = ""`, `topic_id: str = ""`, `metadata: dict`,
  `raw: dict` (platform payload).
- Related types: `Action`, `Attachment`, `Button`, `Block`, `ThreadId`,
  `ChatKind`, `Event/EventKind`, `Reaction`, `Receipt`, `MemberJoin/Leave`.

## 7. Sender / user identity

- `msg.sender` (address/id string) + `msg.thread_id` + `metadata`/`raw`.
- SDK provides **no student database** — mapping Caspian identity →
  `students` row is CampusOps code (see architecture doc § Identity).
- Official allowlist pattern: `CASPIAN_ALLOWED_SENDERS` env, empty = everyone.

## 8. Conversations / threads

- `Thread(thread_id, sink=None)`; commands accumulate as data, then dispatch.
- Models address `thread_id`s, never raw platform chat ids
  (`cx.tools(thread)` hides `thread_id` when bound).
- History backfill: `thread.history(limit=20, before="")`.
- State: `thread.set_state(key, value)`; membership via `subscribe()`.

## 9. Reply

- `thread.post(text, actions=...)` — answers the inbound turn (hosted email =
  threaded `In-Reply-To` reply).
- `thread.reply(reply_to, text, ...)` — quote/specific message.
- `thread.send(text, ...)` — standalone (non-threaded) send.
- Streaming: `with thread.stream(min_chars=24, throttle=0.5) as out:
  out.append(chunk)` — posts once, edits as it writes where the channel
  supports edit; else single post. Never branch per-channel in handler code.

## 10. Proactive messaging

- No scheduler inside the SDK. Proactive = CampusOps job (APScheduler/worker)
  calls the Core Agent, then sends via a persisted `thread_id`:
  `thread.send(...)` / `thread.initiate(...)` (cold DM) /
  `thread.schedule(text, send_at=<epoch>)`.
- Outbound LLM tools: `cx.tools(thread, preset="messenger"|"outbound")`
  (`post_message`, `edit_message`, `add_reaction`, `start_typing`, `send_dm`).

## 11. Rich message blocks

- `thread.send_blocks(blocks, text="", actions=...)` — one provider-neutral
  payload; Slack Block Kit / Discord embeds+buttons / Telegram keyboards render
  natively, email → HTML, text-only channels → clean text fallback.
- `thread.send_media(attachment, caption="")`, `thread.typing()`,
  `thread.edit/react/pin/unpin/delete/forward/mark_read()` per channel
  capabilities (catalog `Capability` enum; agent can never exceed transport).

## 12. Webhooks

- Self-host HTTP: `cx.handle("<channel>", body: bytes, headers: dict) ->
  list[Result]` — verify → parse → step → handlers → send. Signature checks:
  Slack signing secret, Meta `X-Hub-Signature-256`, Telegram secret header,
  X CRC, signed email webhooks; mismatches rejected.
- Hosted inbound: `cx.handle("gateway", body, headers)` — never
  `handle("<channel>", ...)` for a hosted connection (returns `ProvisionError`).
- FastAPI mapping (Phase 1+): one route per self-host channel feeding raw
  body+headers to `cx.handle`; one `/caspian/gateway` route for hosted push
  (when used instead of polling).

## 13. Event handlers

- `on_message` (messages), `on_action` (buttons; `data` filter),
  overlap policies serialize concurrent turns per conversation
  (`queue` default; `ctx.skipped` counts overlap-dropped/queued turns).
- Channel etiquette for system prompts:
  `GET /v1/behavior-prompt` (all) or `/v1/channels/<name>/guide` (one).

## 14. Channel capabilities

`caspian/catalog.py`: `Capability` =
receive/reply/send/media/buttons/blocks/embeds/edit/delete/react/typing/pin/
forward/threading/membership/modals/history/dm/voice/tts/receipts.
`capabilities_of(channel)`, `needs_bot_token(channel, via)`,
`socket_channels()` → `("slack", "discord")`.

## 15. Testing / offline

- `cx.interpret()` → `MemoryInterpreter`, `cx.app.rules` — full handler tests
  with zero network. Adapters consume real platform payload shapes (650+
  upstream tests).
- Live verify: `POST /v1/test-emails {"text": "hello, are you alive?"}` then
  `GET /v1/events?type=message.sent`; agent address printed at
  `channels.add("email", ...)`. New sending domain → check spam first.
- `cx.run(max_iterations=..., interval=...)` / `poll` / `listen` return
  `list[Result]` (`Result.ok/err`, `CaspianError`, `ProvisionError`,
  `AuthRequired`) — assertable in tests. Single run already dedupes;
  exactly-once across restarts = persist own cursor.

## 16. Error handling

- `Result`/`Sent` (`caspian.core.ports`), `CaspianError`/`ProvisionError`
  (`caspian.core.errors`). Handler exceptions don't kill hosted `run()` loop
  (only `Ctrl+C` stops it). Webhook secret mismatches → rejected `Result.err`.
- Gateway refusal during `channels.add` raises (`gateway refused`).

## 17. Lifecycle / listening

| Mode | Call | Blocks? | Needs |
|---|---|---|---|
| Hosted poll | `cx.run()` (`GET /v1/events` loop) | yes | `api_key` |
| Hosted push | `cx.handle("gateway", body, headers)` | per-request | webhook route + secret |
| Self-host webhook | `cx.handle(channel, body, headers)` | per-request | `via="self-host"` + `webhook_url` |
| Self-host poll | `cx.poll("telegram", max_iterations, interval)` | yes | `bot_token` |
| Self-host socket | `cx.listen("discord")` / `cx.listen("slack")` | yes | extras + tokens |

## 18. What Caspian does NOT provide (CampusOps must build)

Scheduler/cron, student DB/auth, Postgres/pgvector memory, Gmail-college
ingestion (Caspian email = the agent's own inbox, not the student's college
mailbox), PDF parsing, LLM/reasoning, deduplication across restarts. Each gets
a clean adapter (see `docs/01-architecture.md`).

## 19. Hard constraints inherited from the official guide

1. Ask the mailbox `username` BEFORE `channels.add("email")`.
2. Never mix hosted/self-host inbound paths.
3. **Never create `caspian/__init__.py`** in our repo — the folder name
   `caspian` with an `__init__.py` shadows the installed SDK. Our adapter
   directory is therefore named `comms/` (see architecture doc).
4. Pass `api_key` explicitly; SDK doesn't read `.env` itself.
5. Discover live hosted channels via `GET /v1/channels`; don't promise
   channels not listed.
