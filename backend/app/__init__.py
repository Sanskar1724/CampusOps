"""Backend package init: load the repo-root `.env` first so every entrypoint
(uvicorn, worker, runner, scripts, tests) sees the same configuration."""

from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:  # pragma: no cover - dotenv is a pinned dependency
    pass
