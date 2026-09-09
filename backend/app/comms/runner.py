"""Live entrypoint: poll the hosted gateway forever.

Run from the repo root:
    python -m backend.app.comms.runner
Requires CASPIAN_API_KEY and CAMPUSOPS_MAILBOX in the environment.
"""

from __future__ import annotations

import os

from backend.app import config
from backend.app.comms.client import build_caspian_app


def main() -> None:
    cx = build_caspian_app(
        api_key=config.CASPIAN_API_KEY,
        mailbox=config.CAMPUSOPS_MAILBOX,
        base_url=config.CASPIAN_BASE_URL,
    )
    print("campusops: polling for inbound — send 'Hello CampusOps' to the agent email")
    cx.run()


if __name__ == "__main__":
    if not os.environ.get("CASPIAN_API_KEY"):
        raise SystemExit("Set CASPIAN_API_KEY first (see .env.example).")
    main()
