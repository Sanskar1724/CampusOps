"""Live entrypoints (run from the repo root).

Hosted gateway poll (email + any hosted channels):
    python -m backend.app.comms.runner
Requires CASPIAN_API_KEY and CAMPUSOPS_MAILBOX.

Telegram self-host poll (no gateway, no public URL — our process calls
Telegram directly). Set TELEGRAM_SELF_HOST=1:
    TELEGRAM_SELF_HOST=1 python -m backend.app.comms.runner
Requires TELEGRAM_BOT_TOKEN only.
"""

from __future__ import annotations

import os

import httpx

from backend.app import config
from backend.app.comms.client import build_caspian_app


def _ensure_polling_mode(token: str) -> None:
    """Telegram delivers to exactly one consumer: an active webhook starves
    `getUpdates` polling (and vice versa). Self-host polling needs the
    webhook removed first — this call is harmless when none is set."""
    try:
        resp = httpx.post(f"https://api.telegram.org/bot{token}/deleteWebhook",
                          json={"drop_pending_updates": False}, timeout=20)
        info = httpx.post(f"https://api.telegram.org/bot{token}/getWebhookInfo",
                          timeout=20).json().get("result", {})
        print(f"campusops: webhook cleared (was: {info.get('url') or 'none'}), "
              f"pending updates: {info.get('pending_update_count', '?')}")
    except Exception as exc:
        print(f"campusops: WARNING — could not clear webhook ({exc}); "
              "the bot may stay silent if Telegram pushes elsewhere.")


def main() -> None:
    if os.environ.get("TELEGRAM_SELF_HOST") == "1":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise SystemExit("Set TELEGRAM_BOT_TOKEN first (see .env.example).")
        _ensure_polling_mode(token)
        print("campusops: ONE runner only — a second poller steals the same updates.")
        cx = build_caspian_app(telegram_bot_token=token, telegram_via="self-host")
        print("campusops: polling Telegram — message your bot (see @Sankiyy_bot)")
        cx.poll("telegram")
        return
    if not os.environ.get("CASPIAN_API_KEY"):
        raise SystemExit("Set CASPIAN_API_KEY first (see .env.example).")
    cx = build_caspian_app(
        api_key=config.CASPIAN_API_KEY,
        mailbox=config.CAMPUSOPS_MAILBOX,
        base_url=config.CASPIAN_BASE_URL,
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    )
    print("campusops: polling for inbound — send 'Hello CampusOps' to the agent email")
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("campusops: NOTE — hosted Telegram claims the bot webhook; do NOT run "
              "a TELEGRAM_SELF_HOST poller at the same time (only one consumer gets updates).")
    cx.run()


if __name__ == "__main__":
    main()
