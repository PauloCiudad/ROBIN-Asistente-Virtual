"""Normalización y búsqueda aproximada de nombres (apps, archivos)."""

from __future__ import annotations

import difflib
import re
import unicodedata


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def score(query: str, candidate: str) -> float:
    """0..1: qué tan bien `candidate` corresponde a `query` (ambos ya normalizados)."""
    if not query or not candidate:
        return 0.0
    if query == candidate:
        return 1.0
    if candidate.startswith(query):
        return 0.92
    words = candidate.split()
    if query in words:
        return 0.88
    if all(token in candidate for token in query.split()):
        return 0.8
    return difflib.SequenceMatcher(None, query, candidate).ratio() * 0.75
