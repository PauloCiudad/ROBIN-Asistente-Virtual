"""Automatizaciones: scripts de Python generados a partir de rutinas detectadas.

Viven en Documentos\\ROBIN\\automatizaciones para que el usuario pueda verlos y editarlos. Un registro
(`automatizaciones.json`) guarda nombre, descripción y si ya se aprobó su primera ejecución.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from robin.actions.files import known_folder
from robin.actions.text_match import normalize, score
from robin.config import data_dir
from robin.learning.patterns import Pattern, Step

log = logging.getLogger(__name__)

_CREATE_NO_WINDOW = 0x08000000
SNOOZE_S = 3 * 86400


@dataclass
class Automation:
    name: str
    file: str
    description: str
    trigger: str
    pattern_id: str
    created: str
    approved: bool = False


def automations_dir() -> Path:
    base = known_folder("documentos") or Path.home() / "Documents"
    path = base / "ROBIN" / "automatizaciones"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize(text)).strip("_")[:50] or "automatizacion"


def script_for(pattern: Pattern, name: str) -> str:
    lines = []
    for step in pattern.steps:
        target = json.dumps(step.target, ensure_ascii=False)
        label = step.label.replace("\n", " ")
        call = {
            "open_app_path": "abrir_programa",
            "open_app_id": "abrir_app",
            "open_path": "abrir",
            "open_url": "abrir_web",
        }[step.kind]
        lines.append(f"    paso({call}, {target}, {json.dumps(label, ensure_ascii=False)})")
    body = "\n".join(lines)
    return f'''"""{name}

Automatización creada por ROBIN el {datetime.now():%Y-%m-%d %H:%M}.
{pattern.description}

Puedes editar este archivo: ROBIN lo ejecuta cuando se lo pides (por ejemplo: "Oye Robin, {pattern.trigger}").
Para probarlo sin abrir nada, ejecútalo con el argumento --dry-run.
"""

import os
import subprocess
import sys
import time
import webbrowser

SIMULAR = "--dry-run" in sys.argv
PAUSA_ENTRE_PASOS = 1.5  # segundos


def abrir_programa(ruta):
    subprocess.Popen([ruta])


def abrir_app(app_id):
    subprocess.Popen(["explorer.exe", "shell:AppsFolder\\\\" + app_id])


def abrir(ruta):
    os.startfile(ruta)


def abrir_web(url):
    webbrowser.open(url)


def paso(accion, destino, descripcion):
    print(("[simulación] " if SIMULAR else "") + "Abriendo " + descripcion)
    if SIMULAR:
        return
    try:
        accion(destino)
    except OSError as error:
        print("  No se pudo abrir " + descripcion + ": " + str(error))
    time.sleep(PAUSA_ENTRE_PASOS)


def main():
{body}


if __name__ == "__main__":
    main()
'''


class AutomationStore:
    def __init__(self, folder: Path | None = None, state_path: Path | None = None) -> None:
        self.folder = folder or automations_dir()
        self._registry = self.folder / "automatizaciones.json"
        self._state_path = state_path or data_dir() / "patterns_state.json"
        self._lock = threading.Lock()

    # --- registro ------------------------------------------------------------------

    def list(self) -> list[Automation]:
        try:
            raw = json.loads(self._registry.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        items = [Automation(**a) for a in raw if isinstance(a, dict)]
        return [a for a in items if (self.folder / a.file).exists()]  # el usuario pudo borrar el archivo

    def _save(self, items: list[Automation]) -> None:
        self._registry.write_text(json.dumps([asdict(a) for a in items], indent=2, ensure_ascii=False),
                                  encoding="utf-8")

    def find(self, name: str) -> Automation | None:
        items = self.list()
        q = normalize(name)
        ranked = sorted(((max(score(q, normalize(a.name)), score(q, normalize(a.trigger))), a) for a in items),
                        key=lambda x: -x[0])
        return ranked[0][1] if ranked and ranked[0][0] >= 0.5 else None

    def has_pattern(self, pattern_id: str) -> bool:
        return any(a.pattern_id == pattern_id for a in self.list())

    def create(self, pattern: Pattern) -> Automation:
        with self._lock:
            name = pattern.title
            file = f"{_slug(name)}.py"
            n = 2
            while (self.folder / file).exists():
                file = f"{_slug(name)}_{n}.py"
                n += 1
            (self.folder / file).write_text(script_for(pattern, name), encoding="utf-8")
            automation = Automation(name=name, file=file, description=pattern.description,
                                    trigger=pattern.trigger, pattern_id=pattern.id,
                                    created=datetime.now().strftime("%Y-%m-%d %H:%M"))
            self._save([*self.list(), automation])
            log.info("Automatización creada: %s", file)
            return automation

    def approve(self, automation: Automation) -> None:
        with self._lock:
            items = self.list()
            for a in items:
                if a.file == automation.file:
                    a.approved = True
            self._save(items)

    def run(self, automation: Automation, dry_run: bool = False) -> subprocess.Popen:
        python = Path(sys.executable)
        pythonw = python.with_name("pythonw.exe")
        exe = str(pythonw if pythonw.exists() and not dry_run else python)
        args = [exe, str(self.folder / automation.file)] + (["--dry-run"] if dry_run else [])
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        if dry_run:
            return subprocess.Popen(args, cwd=self.folder, creationflags=_CREATE_NO_WINDOW, env=env,
                                    stdout=subprocess.PIPE, text=True, encoding="utf-8")
        return subprocess.Popen(args, cwd=self.folder, creationflags=_CREATE_NO_WINDOW, env=env)

    # --- sugerencias (descartadas / pospuestas) --------------------------------------

    def _state(self) -> dict:
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"dismissed": [], "snoozed": {}}

    def _write_state(self, state: dict) -> None:
        self._state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def should_suggest(self, pattern: Pattern) -> bool:
        state = self._state()
        if pattern.id in state.get("dismissed", []) or self.has_pattern(pattern.id):
            return False
        return state.get("snoozed", {}).get(pattern.id, 0) < time.time()

    def snooze(self, pattern_id: str, seconds: float = SNOOZE_S) -> None:
        state = self._state()
        state.setdefault("snoozed", {})[pattern_id] = time.time() + seconds
        self._write_state(state)

    def dismiss(self, pattern_id: str) -> None:
        state = self._state()
        state.setdefault("dismissed", []).append(pattern_id)
        self._write_state(state)

    def reset_suggestions(self) -> None:
        self._write_state({"dismissed": [], "snoozed": {}})


def describe_steps(steps: list[Step]) -> str:
    return ", ".join(s.label for s in steps)


def open_folder(path: Path) -> None:
    os.startfile(path)  # noqa: S606
