"""Engine + sessions. `DATABASE_URL` selects the backend:

- local default: SQLite file (`campusops.db`) — full product works offline.
- production: PostgreSQL, e.g.
  `postgresql+psycopg2://campusops:campusops@db:5432/campusops` (compose).
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models import Base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./campusops.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        try:
            with engine.begin() as conn:
                from sqlalchemy import text as _text
                conn.execute(_text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass  # SQLite or pgvector not available — fallback embeddings still work
    Base.metadata.create_all(bind=engine)
    ensure_columns()


def ensure_columns() -> None:
    """Lightweight migration for databases created before a column existed.
    `create_all` never adds columns to existing tables, so new fields get an
    explicit ALTER TABLE here (SQLite + PostgreSQL)."""
    from sqlalchemy import inspect, text as sql_text
    wanted = {
        "students": [("telegram_chat_id", "VARCHAR(64) NOT NULL DEFAULT ''")],
        "notifications": [("error", "VARCHAR(500) NOT NULL DEFAULT ''")],
    }
    with engine.begin() as conn:
        existing_tables = set(inspect(conn).get_table_names())
        for table, columns in wanted.items():
            if table not in existing_tables:
                continue
            present = {c["name"] for c in inspect(conn).get_columns(table)}
            for name, ddl in columns:
                if name not in present:
                    conn.execute(sql_text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
