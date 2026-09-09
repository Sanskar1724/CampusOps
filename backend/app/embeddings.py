"""Portable embeddings: deterministic token-hash vectors + cosine similarity.

Runs on SQLite and PostgreSQL with zero extra services. Production path is a
drop-in: swap `embed()` for a real model and move `embedding_json` into a
pgvector column with an ANN index — retrieval already goes through
`most_similar()` in one place.
"""

from __future__ import annotations

import hashlib
import json
import math
import re

DIM = 128
_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def embed(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    for token in _TOKEN.findall(text.lower()):
        slot = int(hashlib.md5(token.encode()).hexdigest(), 16) % dim
        vec[slot] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def dumps(vec: list[float]) -> str:
    return json.dumps([round(v, 6) for v in vec])


def loads(raw: str) -> list[float]:
    try:
        vec = json.loads(raw)
        return [float(v) for v in vec] if isinstance(vec, list) else []
    except (ValueError, TypeError):
        return []


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def most_similar(query: str, candidates: list[tuple[int, str]], top_k: int = 5):
    """candidates: (id, text). Returns [(id, score)] sorted desc."""
    q = embed(query)
    scored = [(cid, cosine(q, embed(text))) for cid, text in candidates]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]
