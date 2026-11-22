"""Herramientas que ROBIN ofrece al modelo ("dynamic tools" del Codex app-server).

El modelo no ejecuta comandos: solo puede pedir estas acciones concretas, y ROBIN las valida y ejecuta.
Todas respetan el switch "Abrir apps, archivos y webs" (`allow_open_apps`).
"""

from __future__ import annotations

import json
import logging
import os
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from robin.actions.apps import AppIndex
from robin.actions.files import BLOCKED_EXTENSIONS, default_search_roots, find_files, resolve_path

log = logging.getLogger(__name__)


def _spec(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOL_SPECS = [
    _spec(
        "open_app",
        "Abre una aplicación instalada en el PC del usuario (menú Inicio). Windows puede estar en inglés: "
        "si no la encuentra, devuelve sugerencias con los nombres reales.",
        {"name": {"type": "string", "description": "Nombre de la app, p. ej. 'Spotify', 'Excel', 'calculadora'."}},
        ["name"],
    ),
    _spec(
        "open_url",
        "Abre una página web en el navegador predeterminado. Para buscar algo, arma la URL de búsqueda "
        "(Google, YouTube, etc.).",
        {"url": {"type": "string", "description": "URL completa que empiece por https:// o http://"}},
        ["url"],
    ),
    _spec(
        "open_path",
        "Abre una carpeta o un documento (PDF, Word, Excel, imagen, video…) con su programa predeterminado. "
        "Acepta rutas absolutas o carpetas conocidas: escritorio, documentos, descargas, imagenes, musica, videos. "
        "No abre programas ni scripts (para apps usa open_app).",
        {"path": {"type": "string", "description": "Ruta absoluta o nombre de carpeta conocida."}},
        ["path"],
    ),
    _spec(
        "find_files",
        "Busca archivos o carpetas por nombre (los más recientes primero). Por defecto busca en escritorio, "
        "documentos y descargas. Úsalo antes de open_path cuando no sepas la ruta exacta.",
        {
            "query": {"type": "string", "description": "Palabras del nombre del archivo, p. ej. 'informe ventas'."},
            "folder": {"type": "string", "description": "Opcional: carpeta donde buscar (ruta o carpeta conocida)."},
        },
        ["query"],
    ),
    _spec(
        "list_automations",
        "Lista las automatizaciones (scripts de rutinas) que ROBIN creó para el usuario.",
        {},
        [],
    ),
    _spec(
        "run_automation",
        "Ejecuta una automatización creada por ROBIN (por ejemplo la rutina de inicio del día). "
        "La primera vez el usuario debe aprobarla; ROBIN se encarga de pedírselo.",
        {"name": {"type": "string", "description": "Nombre o descripción de la automatización."}},
        ["name"],
    ),
]


@dataclass
class ToolResult:
    success: bool
    text: str  # lo que lee el modelo
    note: str | None = None  # lo que se muestra al usuario en el chat


class ActionRunner:
    def __init__(
        self,
        is_allowed: Callable[[], bool],
        on_action: Callable[[str, str, dict], None] | None = None,
        automations=None,
        confirm: Callable[[str], bool] | None = None,
    ) -> None:
        self._is_allowed = is_allowed
        self._on_action = on_action  # registro de actividad (Fase 3)
        self._automations = automations  # AutomationStore
        self._confirm = confirm  # pide permiso al usuario (bloquea hasta respuesta)
        self.apps = AppIndex()
        self.apps.warm_up()
        self._handlers = {
            "open_app": self._open_app,
            "open_url": self._open_url,
            "open_path": self._open_path,
            "find_files": self._find_files,
            "list_automations": self._list_automations,
            "run_automation": self._run_automation,
        }

    def _record(self, kind: str, label: str, meta: dict) -> None:
        if self._on_action is not None:
            try:
                self._on_action(kind, label, meta)
            except Exception:
                log.exception("No se pudo registrar la acción")

    def run(self, tool: str, arguments) -> ToolResult:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        handler = self._handlers.get(tool)
        if handler is None:
            return ToolResult(False, f"Herramienta desconocida: {tool}")
        if not self._is_allowed():
            return ToolResult(
                False,
                "El usuario tiene desactivado 'Abrir apps, archivos y webs'. Dile que puede activarlo en "
                "Ajustes > Acciones.",
            )
        try:
            result = handler(**{k: v for k, v in arguments.items() if isinstance(v, str)})
        except TypeError:
            return ToolResult(False, "Faltan argumentos para la herramienta.")
        except Exception as exc:
            log.exception("Fallo ejecutando %s", tool)
            return ToolResult(False, f"No se pudo completar la acción: {exc}")
        log.info("Acción %s → %s", tool, "ok" if result.success else "falló")
        return result

    # --- herramientas ----------------------------------------------------------

    def _open_app(self, name: str) -> ToolResult:
        matches = self.apps.search(name)
        if not matches or matches[0][0] < 0.6:
            suggestions = ", ".join(a.name for _, a in matches) or "ninguna parecida"
            return ToolResult(False, f"No encontré una app llamada '{name}'. Parecidas: {suggestions}.")
        app = matches[0][1]
        self.apps.launch(app)
        self._record("open_app", app.name, {"app_id": app.app_id})
        return ToolResult(True, f"Abrí la app '{app.name}'.", f"Abriendo {app.name}")

    def _open_url(self, url: str) -> ToolResult:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return ToolResult(False, "Solo puedo abrir direcciones web que empiecen por http:// o https://.")
        webbrowser.open(url.strip())
        self._record("open_url", url.strip(), {"url": url.strip()})
        return ToolResult(True, f"Abrí {url} en el navegador.", f"Abriendo {parsed.netloc}")

    def _open_path(self, path: str) -> ToolResult:
        target = resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"No existe: {target}. Puedes buscarlo con find_files.")
        if target.is_file() and target.suffix.casefold() in BLOCKED_EXTENSIONS:
            return ToolResult(False, "Por seguridad no abro programas ni scripts con open_path; usa open_app.")
        os.startfile(target)  # noqa: S606 — abre con el programa predeterminado
        self._record("open_path", target.name or str(target), {"path": str(target)})
        return ToolResult(True, f"Abrí {target}.", f"Abriendo {target.name or target}")

    def _find_files(self, query: str, folder: str | None = None) -> ToolResult:
        roots = [resolve_path(folder)] if folder else default_search_roots()
        roots = [r for r in roots if r.exists()]
        if not roots:
            return ToolResult(False, "No encontré la carpeta donde buscar.")
        found = find_files(query, roots)
        if not found:
            where = ", ".join(str(r) for r in roots)
            return ToolResult(True, f"No encontré nada con '{query}' en {where}.")
        listing = "\n".join(str(p) for p in found)
        return ToolResult(True, f"Encontré (más recientes primero):\n{listing}")

    def _list_automations(self) -> ToolResult:
        if self._automations is None:
            return ToolResult(False, "Las automatizaciones no están disponibles.")
        items = self._automations.list()
        if not items:
            return ToolResult(True, "Todavía no hay automatizaciones. Las propongo cuando detecto una rutina repetida.")
        listing = "\n".join(f"- {a.name}: {a.description}" for a in items)
        return ToolResult(True, f"Automatizaciones del usuario:\n{listing}")

    def _run_automation(self, name: str) -> ToolResult:
        if self._automations is None:
            return ToolResult(False, "Las automatizaciones no están disponibles.")
        automation = self._automations.find(name)
        if automation is None:
            names = ", ".join(a.name for a in self._automations.list()) or "ninguna"
            return ToolResult(False, f"No encontré la automatización '{name}'. Existentes: {names}.")
        if not automation.approved:
            question = (f"Es la primera vez que ejecuto «{automation.name}». {automation.description} "
                        "¿La ejecuto?")
            if self._confirm is None or not self._confirm(question):
                return ToolResult(False, "El usuario no aprobó ejecutar la automatización; no se hizo nada.")
            self._automations.approve(automation)
        self._automations.run(automation)
        return ToolResult(True, f"Ejecuté la automatización '{automation.name}'.", f"Ejecutando {automation.name}")
