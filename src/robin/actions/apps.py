"""Índice de apps instaladas (las mismas del menú Inicio, incluidas las de la Microsoft Store)."""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from dataclasses import dataclass

from robin.actions.text_match import normalize, score

log = logging.getLogger(__name__)

_CREATE_NO_WINDOW = 0x08000000
_REFRESH_SECONDS = 600

# Windows puede estar en inglés: nombres comunes en español → nombre real probable.
SPANISH_ALIASES = {
    "calculadora": "calculator",
    "bloc de notas": "notepad",
    "notas": "notepad",
    "configuracion": "settings",
    "ajustes": "settings",
    "explorador": "file explorer",
    "explorador de archivos": "file explorer",
    "archivos": "file explorer",
    "camara": "camera",
    "reloj": "clock",
    "alarma": "clock",
    "calendario": "calendar",
    "correo": "outlook",
    "fotos": "photos",
    "recortes": "snipping tool",
    "captura": "snipping tool",
    "terminal": "terminal",
    "tienda": "microsoft store",
    "word": "word",
    "excel": "excel",
    "powerpoint": "powerpoint",
}


@dataclass(frozen=True)
class App:
    name: str
    app_id: str


class AppIndex:
    def __init__(self) -> None:
        self._apps: list[App] = []
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        threading.Thread(target=self._load, name="robin-app-index", daemon=True).start()

    def _load(self) -> list[App]:
        with self._lock:
            if self._apps and time.time() - self._loaded_at < _REFRESH_SECONDS:
                return self._apps
            try:
                out = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     # PowerShell 5.1 escribe en la página de códigos OEM si no se fuerza UTF-8.
                     "[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
                     "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"],
                    capture_output=True, text=True, encoding="utf-8", timeout=20,
                    creationflags=_CREATE_NO_WINDOW,
                ).stdout
                raw = json.loads(out or "[]")
                if isinstance(raw, dict):
                    raw = [raw]
                self._apps = [App(a["Name"], a["AppID"]) for a in raw if a.get("Name") and a.get("AppID")]
                self._loaded_at = time.time()
                log.info("Índice de apps cargado: %d apps", len(self._apps))
            except Exception:
                log.exception("No se pudo leer la lista de apps")
            return self._apps

    def search(self, query: str, limit: int = 5) -> list[tuple[float, App]]:
        apps = self._load()
        q = normalize(query)
        q = SPANISH_ALIASES.get(q, q)
        ranked = sorted(((score(q, normalize(a.name)), a) for a in apps), key=lambda x: -x[0])
        return [r for r in ranked[:limit] if r[0] > 0.3]

    def launch(self, app: App) -> None:
        subprocess.Popen(
            ["explorer.exe", f"shell:AppsFolder\\{app.app_id}"], creationflags=_CREATE_NO_WINDOW
        )
