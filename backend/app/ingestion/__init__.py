"""Generic ingestion contracts. New sources (Moodle, WhatsApp, portal) implement
`InformationSource` and reuse the normalizer → extractor → relevance →
memory pipeline without touching the Core Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass
class RawItem:
    external_id: str
    title: str
    body: str
    sender: str = ""
    received_at: datetime | None = None
    meta: dict = field(default_factory=dict)


class InformationSource(Protocol):
    name: str

    def fetch(self, db: Session, student_id: int) -> list[RawItem]: ...
