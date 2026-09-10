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

from backend.app import config
from backend.app.comms.client import build_caspian_app


def main() -> None:
    if os.environ.get("TELEGRAM_SELF_HOST") == "1":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise SystemExit("Set TELEGRAM_BOT_TOKEN first (see .env.example).")
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
    cx.run()


if __name__ == "__main__":
    main()
