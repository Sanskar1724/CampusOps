"""Re-export of the ingestion contracts (canonical home: `ingestion/__init__.py`)."""

from backend.app.ingestion import InformationSource, RawItem

__all__ = ["InformationSource", "RawItem"]
