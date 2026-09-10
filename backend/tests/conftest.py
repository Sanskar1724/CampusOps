"""Isolated tests: in-memory SQLite, patched sessions, deterministic LLM.
Never touches campusops.db or the network."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.agents.core as core
import backend.app.comms.handlers as handlers
import backend.app.db as db_module
import backend.app.ingestion.extract as extract
from backend.app.llm import DevLLM
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
    # Deterministic composer: tests verify retrieval + wiring, never provider mood.
    monkeypatch.setattr(core, "get_llm", lambda: DevLLM())
    monkeypatch.setattr(extract, "get_llm", lambda: DevLLM())

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
