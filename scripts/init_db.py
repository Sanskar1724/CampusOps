"""Create all tables (idempotent). Usage: python -m scripts.init_db [--seed]"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from backend.app.db import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    print("database ready")
    if "--seed" in sys.argv:
        from scripts.seed_demo import seed  # noqa: E402
        seed()
