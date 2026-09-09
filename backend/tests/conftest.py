"""Isolated tests: in-memory SQLite, patched sessions. Never touches campusops.db."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.comms.handlers as handlers
import backend.app.db as db_module
from backend.app.main import app
from backend.app.models import Base


@pytest.fixture()
def db_session(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db_module, "SessionLocal", factory)
    monkeypatch.setattr(handlers, "SessionLocal", factory)

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[db_module.get_db] = override_get_db
    session = factory()
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()
