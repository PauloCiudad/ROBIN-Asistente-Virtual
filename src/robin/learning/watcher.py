"""Busca rutinas cada cierto tiempo y propone la primera que merezca una automatización."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer, Signal

from robin.learning.activity import ActivityLog
from robin.learning.automations import AutomationStore
from robin.learning.patterns import Pattern, detect_patterns

log = logging.getLogger(__name__)

SCAN_EVERY_MS = 20 * 60 * 1000
FIRST_SCAN_MS = 2 * 60 * 1000


class PatternWatcher(QObject):
    suggestion = Signal(object)  # Pattern

    def __init__(self, activity: ActivityLog, store: AutomationStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._activity = activity
        self._store = store
        self.pending: Pattern | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.scan)
        self._timer.start(SCAN_EVERY_MS)
        QTimer.singleShot(FIRST_SCAN_MS, self.scan)

    def scan(self) -> int:
        """Devuelve cuántas rutinas nuevas hay; emite `suggestion` con la mejor."""
        if self.pending is not None:
            return 1
        try:
            patterns = [p for p in detect_patterns(self._activity.events(since_days=14))
                        if self._store.should_suggest(p)]
        except Exception:
            log.exception("Fallo buscando patrones")
            return 0
        log.info("Búsqueda de rutinas: %d nuevas", len(patterns))
        if patterns:
            self.pending = patterns[0]
            self.suggestion.emit(patterns[0])
        return len(patterns)

    def answer(self, choice: str) -> object | None:
        """'create' → crea la automatización y la devuelve; 'later' → pospone; 'never' → descarta."""
        pattern, self.pending = self.pending, None
        if pattern is None:
            return None
        if choice == "create":
            return self._store.create(pattern)
        if choice == "never":
            self._store.dismiss(pattern.id)
        else:
            self._store.snooze(pattern.id)
        return None
