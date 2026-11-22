"""Rutas de datos y ajustes persistentes de ROBIN."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from logging.handlers import RotatingFileHandler
from pathlib import Path

from robin import APP_NAME

log = logging.getLogger(__name__)


def data_dir() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _subdir(name: str) -> Path:
    path = data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def codex_home() -> Path:
    """CODEX_HOME propio de ROBIN: sesión de ChatGPT aislada de otras instalaciones de Codex."""
    return _subdir("codex")


def workspace_dir() -> Path:
    return _subdir("workspace")


def logs_dir() -> Path:
    return _subdir("logs")


def models_dir() -> Path:
    return _subdir("models")


def voice_dir() -> Path:
    """Perfil de voz del usuario (muestras de la configuración inicial, huella de voz). Solo local."""
    return _subdir("voice")


def settings_path() -> Path:
    return data_dir() / "settings.json"


@dataclass
class Settings:
    # Perfil
    user_name: str = ""
    onboarding_done: bool = False
    # General
    start_with_windows: bool = False
    auto_hide: bool = True  # ocultar al tray cuando ROBIN termina de responder
    # Voz (Fase 2)
    voice_enabled: bool = True
    wake_word_enabled: bool = True
    owner_voice_only: bool = True  # "Oye Robin" solo con la voz del usuario (si hay huella de voz)
    tts_voice: str = "es-PE-CamilaNeural"
    # Acciones (Fase 2)
    allow_open_apps: bool = True
    use_chatgpt_apps: bool = True  # Google Calendar, Gmail… conectados en la cuenta de ChatGPT
    # Aprendizaje de patrones (Fase 3) — ver ADR-003
    observe_requests: bool = True
    observe_apps: bool = False
    observe_files: bool = False
    observe_keyboard: bool = False

    @classmethod
    def load(cls) -> Settings:
        path = settings_path()
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.warning("settings.json ilegible; se usan valores por defecto")
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self) -> None:
        path = settings_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


def setup_logging() -> None:
    handler = RotatingFileHandler(
        logs_dir() / "robin.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
