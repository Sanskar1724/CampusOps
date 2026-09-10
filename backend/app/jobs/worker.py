"""Worker entrypoint: `python -m backend.app.jobs.worker`. Loops forever
(default 60s): briefs, reminder/deadline sweeps, queued-delivery retries."""

from __future__ import annotations

import os
import time
import traceback

from backend.app.db import SessionLocal, init_db
from backend.app.jobs import run_all
from backend.app.models import utcnow

INTERVAL = int(os.environ.get("WORKER_INTERVAL_SECONDS", "60"))


def main() -> None:
    init_db()
    print(f"campusops worker: every {INTERVAL}s")
    while True:
        db = SessionLocal()
        try:
            result = run_all(db, utcnow())
            if any(result.values()):
                print(f"worker: {result}")
        except Exception:
            traceback.print_exc()
        finally:
            db.close()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
