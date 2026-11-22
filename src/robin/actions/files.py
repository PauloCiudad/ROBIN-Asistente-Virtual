"""Carpetas conocidas del usuario y búsqueda rápida de archivos."""

from __future__ import annotations

import os
import time
import winreg
from pathlib import Path

from robin.actions.text_match import normalize

_SHELL_FOLDERS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
_KNOWN = {
    "escritorio": "Desktop",
    "documentos": "Personal",
    "descargas": "{374DE290-123F-4565-9164-39C4925E467B}",
    "imagenes": "My Pictures",
    "musica": "My Music",
    "videos": "My Video",
}
_ALIASES = {"desktop": "escritorio", "documents": "documentos", "downloads": "descargas",
            "pictures": "imagenes", "fotos": "imagenes", "music": "musica", "video": "videos"}

# Nunca se abren con open_path: ejecutarían código. Las apps se abren con open_app.
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".com", ".ps1", ".psm1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
    ".msi", ".msp", ".scr", ".pif", ".reg", ".lnk", ".hta", ".cpl", ".jar", ".py", ".pyw",
}
_SKIP_DIRS = {"appdata", "node_modules", ".git", "__pycache__", ".venv", "venv", "$recycle.bin"}


def known_folder(name: str) -> Path | None:
    key = normalize(name)
    key = _ALIASES.get(key, key)
    value_name = _KNOWN.get(key)
    if value_name is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SHELL_FOLDERS) as k:
            raw, _ = winreg.QueryValueEx(k, value_name)
        return Path(os.path.expandvars(raw))
    except OSError:
        return None


def resolve_path(text: str) -> Path:
    """Acepta una carpeta conocida ('descargas'), una ruta con variables (%USERPROFILE%) o ~."""
    folder = known_folder(text)
    if folder is not None:
        return folder
    return Path(os.path.expanduser(os.path.expandvars(text.strip().strip('"'))))


def default_search_roots() -> list[Path]:
    roots = [known_folder(n) for n in ("escritorio", "documentos", "descargas")]
    return [r for r in roots if r is not None and r.exists()]


def find_files(query: str, roots: list[Path], limit: int = 10, max_depth: int = 5,
               time_budget: float = 3.0) -> list[Path]:
    tokens = normalize(query).split()
    if not tokens:
        return []
    deadline = time.monotonic() + time_budget
    found: list[tuple[float, Path]] = []
    stack = [(root, 0) for root in roots]
    while stack and time.monotonic() < deadline:
        folder, depth = stack.pop()
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        for entry in entries:
            name = entry.name
            if name.startswith(".") or name.casefold() in _SKIP_DIRS:
                continue
            norm = normalize(name)
            if all(t in norm for t in tokens):
                try:
                    found.append((entry.stat().st_mtime, Path(entry.path)))
                except OSError:
                    pass
            if entry.is_dir(follow_symlinks=False) and depth < max_depth:
                stack.append((Path(entry.path), depth + 1))
    found.sort(key=lambda x: -x[0])  # los más recientes primero
    return [p for _, p in found[:limit]]
