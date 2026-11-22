"""Qué archivos recientes vale la pena aprender (documentos, no programas ni carpetas del sistema)."""

from __future__ import annotations

import os

from robin.actions.files import BLOCKED_EXTENSIONS


def is_trackable_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].casefold()
    if not ext or ext in BLOCKED_EXTENSIONS:
        return False
    lowered = path.casefold()
    if "\\appdata\\" in lowered or "\\windows\\" in lowered or "\\temp\\" in lowered:
        return False
    return os.path.isfile(path)
