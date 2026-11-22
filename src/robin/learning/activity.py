"""Registro local de actividad para detectar patrones (Fase 3). SQLite en %APPDATA%\\ROBIN\\activity.db.

Solo guarda lo mínimo: qué acción, qué app (nombre del ejecutable, nunca títulos de ventana) o qué archivo.
El usuario puede borrarlo todo desde Ajustes.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from robin.config import data_dir

RETENTION_DAYS = 60


@dataclass
class Event:
    ts: float
    source: str  # "request" | "action" | "app" | "file"
    kind: str  # p. ej. "open_app", "app_open", "file_open"
    value: str  # etiqueta legible (nombre de app, archivo, URL…)
    meta: dict = field(default_factory=dict)

    @property
    def day(self) -> str:
        return datetime.fromtimestamp(self.ts).strftime("%Y-%m-%d")


class ActivityLog:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or data_dir() / "activity.db"
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self._path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS events (ts REAL, source TEXT, kind TEXT, value TEXT, meta TEXT)"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS events_ts ON events(ts)")
        self._db.commit()
        self.prune()

    def record(self, source: str, kind: str, value: str, meta: dict | None = None, ts: float | None = None) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                (ts or time.time(), source, kind, value, json.dumps(meta or {}, ensure_ascii=False)),
            )
            self._db.commit()

    def events(self, since_days: float = 14, source: str | None = None) -> list[Event]:
        since = time.time() - since_days * 86400
        query, args = "SELECT ts, source, kind, value, meta FROM events WHERE ts >= ?", [since]
        if source:
            query += " AND source = ?"
            args.append(source)
        with self._lock:
            rows = self._db.execute(query + " ORDER BY ts", args).fetchall()
        return [Event(ts, src, kind, value, json.loads(meta or "{}")) for ts, src, kind, value, meta in rows]

    def count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def clear(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM events")
            self._db.commit()

    def prune(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM events WHERE ts < ?", (time.time() - RETENTION_DAYS * 86400,))
            self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()
