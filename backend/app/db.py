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
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
