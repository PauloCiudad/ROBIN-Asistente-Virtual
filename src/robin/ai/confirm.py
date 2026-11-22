"""Confirmación del usuario antes de que una app conectada (Calendar, Gmail…) cree, cambie, borre o envíe algo.

Codex pide permiso con `mcpServer/elicitation/request` (política granular `mcp_elicitations=True`). Esa petición
llega en el hilo lector del SDK, que queda esperando aquí hasta que el usuario responde (botón o voz) o se
agota el tiempo. Sin respuesta = no se hace nada.
"""

from __future__ import annotations

import logging
import threading
import webbrowser

from PySide6.QtCore import QObject, Signal

from robin.actions.text_match import normalize

log = logging.getLogger(__name__)

TIMEOUT_S = 60

_YES = {"si", "claro", "dale", "confirmo", "confirmado", "hazlo", "ok", "okay", "de acuerdo", "adelante",
        "correcto", "yes", "ya", "por supuesto", "si hazlo", "si por favor", "afirmativo", "procede", "acepto"}
_NO = {"no", "cancela", "cancelar", "cancelalo", "espera", "mejor no", "negativo", "nada", "para", "detente",
       "no gracias", "no lo hagas", "todavia no"}


def parse_yes_no(text: str) -> bool | None:
    """'Sí, hazlo' → True; 'No, mejor no' → False; cualquier otra cosa → None."""
    norm = normalize(text)
    if not norm:
        return None
    words = norm.split()
    if norm in _NO or words[0] in ("no", "cancela", "cancelar", "cancelalo"):
        return False
    if norm in _YES or words[0] in ("si", "claro", "dale", "ok", "okay", "hazlo", "confirmo", "adelante", "yes"):
        return True
    return None


def _accept_content(schema) -> dict | None:
    """Contenido para aceptar un formulario de aprobación. None si pide datos que ROBIN no sabe rellenar."""
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties") or {}
    content: dict = {}
    for name, spec in props.items():
        kind = spec.get("type") if isinstance(spec, dict) else None
        options = [str(o) for o in (spec.get("enum") or [])] if isinstance(spec, dict) else []
        if kind == "boolean":
            content[name] = True
        elif options:
            approve = [o for o in options if normalize(o) in ("accept", "approve", "allow", "yes", "si", "permitir",
                                                               "aprobar", "aceptar", "allow once", "approve once")]
            if not approve:
                return None
            content[name] = approve[0]
        elif name in (schema.get("required") or []):
            return None  # p. ej. texto libre obligatorio
    return content


def describe(params: dict) -> str:
    message = str(params.get("message") or "Una app quiere hacer un cambio.").strip()
    server = str(params.get("serverName") or "").strip()
    return f"{server}: {message}" if server and server.casefold() not in message.casefold() else message


class ConfirmationBroker(QObject):
    """Puente hilo-lector ⇄ interfaz. `ask()` bloquea; la interfaz llama a `resolve()`."""

    requested = Signal(str)  # texto para mostrar al usuario
    finished = Signal(bool)  # decisión final (también por tiempo agotado)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._event: threading.Event | None = None
        self._answer = False
        self._lock = threading.Lock()

    @property
    def pending(self) -> bool:
        return self._event is not None

    def ask(self, text: str, timeout: float = TIMEOUT_S) -> bool:
        with self._lock:
            event = threading.Event()
            self._event, self._answer = event, False
        self.requested.emit(text)
        answered = event.wait(timeout)
        with self._lock:
            decision = self._answer if answered else False
            self._event = None
        log.info("Confirmación de acción: %s", "aceptada" if decision else ("rechazada" if answered else "sin respuesta"))
        self.finished.emit(decision)
        return decision

    def resolve(self, accepted: bool) -> None:
        with self._lock:
            if self._event is not None:
                self._answer = accepted
                self._event.set()

    # --- traducción de peticiones del runtime a respuestas ---------------------------

    def handle_elicitation(self, params: dict) -> dict:
        mode = params.get("mode")
        if mode == "url":
            url = str(params.get("url", ""))
            if url.startswith("https://") and self.ask(f"{describe(params)}\n\nSe abrirá: {url}"):
                webbrowser.open(url)
                return {"action": "accept"}
            return {"action": "decline"}
        if mode in ("form", "openai/form", "openaiForm"):
            content = _accept_content(params.get("requestedSchema"))
            if content is None:
                log.info("Formulario de app con datos que ROBIN no sabe rellenar: rechazado")
                return {"action": "decline"}
            if self.ask(describe(params)):
                return {"action": "accept", "content": content}
            return {"action": "decline"}
        return {"action": "decline"}  # p. ej. verificación de dispositivo: no soportada

    def handle_user_input(self, params: dict) -> dict:
        """Preguntas con opciones (experimental): se aceptan solo las de tipo aprobar/denegar."""
        answers: dict = {}
        for q in params.get("questions") or []:
            options = [o.get("label", "") for o in (q.get("options") or [])]
            approve = [o for o in options if normalize(o).split()[:1] in (["allow"], ["approve"], ["yes"], ["si"],
                                                                         ["permitir"], ["aprobar"], ["accept"])]
            deny = [o for o in options if o not in approve]
            if not approve:
                answers[q.get("id", "")] = {"answers": []}
                continue
            accepted = self.ask(str(q.get("question") or q.get("header") or "¿Lo confirmo?"))
            choice = approve[0] if accepted else (deny[0] if deny else None)
            answers[q.get("id", "")] = {"answers": [choice] if choice else []}
        return {"answers": answers}
