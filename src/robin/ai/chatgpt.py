"""Conexión con ChatGPT mediante "Sign in with ChatGPT" (Codex app-server). Sin API keys (ADR-000).

`ChatGPTService` vive en un QThread propio: todas las llamadas al SDK son bloqueantes, así que la
interfaz se comunica con él solo mediante señales.
"""

from __future__ import annotations

import logging
import os
import webbrowser
from enum import Enum

from PySide6.QtCore import QObject, QThread, Signal, Slot

from robin import APP_NAME, __version__
from robin.actions.tools import TOOL_SPECS, ActionRunner
from robin.ai.confirm import ConfirmationBroker
from robin.ai.persona import persona_for
from robin.config import codex_home, workspace_dir

log = logging.getLogger(__name__)

# ROBIN solo actúa en el PC mediante sus propias herramientas (robin.actions): se apagan la terminal y
# demás herramientas integradas de Codex.
_CODEX_OVERRIDES = (
    "features.shell_tool=false",
    "features.computer_use=false",
    "features.browser_use=false",
    "features.browser_use_external=false",
    "features.image_generation=false",
)


class AIState(str, Enum):
    STARTING = "starting"
    NEEDS_LOGIN = "needs_login"
    LOGGING_IN = "logging_in"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


class ChatGPTService(QObject):
    state_changed = Signal(str, str)  # (AIState, mensaje para el usuario)
    account_changed = Signal(str)  # descripción de la cuenta, "" si no hay sesión
    reply_started = Signal()
    reply_delta = Signal(str)
    reply_finished = Signal(str)  # texto completo
    reply_failed = Signal(str)
    action_performed = Signal(str)  # aviso breve para el chat, p. ej. "Abriendo Spotify"

    def __init__(self, actions: ActionRunner | None = None, user_name: str = "",
                 confirmer: ConfirmationBroker | None = None, use_apps: bool = True) -> None:
        super().__init__()
        self._actions = actions
        self._user_name = user_name
        self._confirmer = confirmer
        self._use_apps = use_apps
        self._codex = None
        self._thread = None
        self._login = None
        self._turn = None

    # --- ciclo de vida ---------------------------------------------------------

    @Slot()
    def start(self) -> None:
        self._set_state(AIState.STARTING, "Conectando con ChatGPT…")
        self._close_codex()
        try:
            from openai_codex import Codex, CodexConfig

            env = dict(os.environ, CODEX_HOME=str(codex_home()))
            self._codex = Codex(
                CodexConfig(
                    env=env,
                    cwd=str(workspace_dir()),
                    client_name="robin",
                    client_title=APP_NAME,
                    client_version=__version__,
                    # Sin el switch "Usar mis apps de ChatGPT", se apagan también los conectores.
                    config_overrides=_CODEX_OVERRIDES + (() if self._use_apps else ("features.apps=false",)),
                )
            )
            # El SDK no expone un manejador para las llamadas a herramientas propias; se sustituye el de
            # aprobaciones del cliente (que por defecto ACEPTA comandos y cambios de archivos).
            self._codex._client._approval_handler = self._handle_server_request
            self._refresh_account()
        except Exception as exc:  # el runtime puede faltar o fallar al arrancar
            log.exception("No se pudo iniciar el runtime de Codex")
            self._set_state(AIState.ERROR, f"No pude iniciar la conexión con ChatGPT: {exc}")

    @Slot()
    def shutdown(self) -> None:
        """Cierra el runtime y termina el hilo en el que vive este servicio."""
        self._close_codex()
        QThread.currentThread().quit()

    def _close_codex(self) -> None:
        self._thread = None
        if self._codex is not None:
            try:
                self._codex.close()
            except Exception:
                log.exception("Error cerrando Codex")
            self._codex = None

    # --- cuenta ----------------------------------------------------------------

    def _refresh_account(self) -> None:
        response = self._codex.account()
        account = response.account.root if response.account is not None else None
        if account is None or getattr(account, "type", None) != "chatgpt":
            self.account_changed.emit("")
            self._set_state(AIState.NEEDS_LOGIN, "Conecta tu cuenta de ChatGPT para empezar.")
            return
        plan = getattr(account.plan_type, "value", account.plan_type)
        self.account_changed.emit(f"{account.email or 'Cuenta de ChatGPT'} · plan {plan}")
        self._thread = None
        self._set_state(AIState.READY, "")

    @Slot()
    def login(self) -> None:
        if self._codex is None:
            return
        if self._login is not None:
            try:
                self._login.cancel()
            except Exception:
                pass
        self._set_state(AIState.LOGGING_IN, "Completa el inicio de sesión en el navegador…")
        try:
            self._login = self._codex.login_chatgpt()
            webbrowser.open(self._login.auth_url)
            result = self._login.wait()
        except Exception as exc:
            log.exception("Fallo en el login con ChatGPT")
            self._set_state(AIState.NEEDS_LOGIN, f"No se pudo iniciar sesión: {exc}")
            return
        finally:
            self._login = None
        if not result.success:
            self._set_state(AIState.NEEDS_LOGIN, f"No se pudo iniciar sesión: {result.error or 'cancelado'}")
            return
        self._refresh_account()

    def cancel_login(self) -> None:
        """Seguro de llamar desde otro hilo: cancela el login en curso (desbloquea `wait()`)."""
        handle = self._login
        if handle is not None:
            try:
                handle.cancel()
            except Exception:
                log.exception("No se pudo cancelar el login")

    @Slot()
    def logout(self) -> None:
        if self._codex is None:
            return
        try:
            self._codex.logout()
        except Exception:
            log.exception("Error al cerrar sesión")
        self._thread = None
        self.account_changed.emit("")
        self._set_state(AIState.NEEDS_LOGIN, "Sesión cerrada. Conecta tu cuenta de ChatGPT para seguir.")

    # --- conversación ----------------------------------------------------------

    @Slot()
    def new_conversation(self) -> None:
        self._thread = None

    @Slot(bool)
    def set_use_apps(self, enabled: bool) -> None:
        """Activar/desactivar las apps conectadas exige reiniciar el runtime de Codex (≈3 s)."""
        if enabled != self._use_apps:
            self._use_apps = enabled
            log.info("Apps de ChatGPT %s: reiniciando runtime", "activadas" if enabled else "desactivadas")
            self.start()

    @Slot(str)
    def set_user_name(self, name: str) -> None:
        self._user_name = name
        self._thread = None  # el próximo hilo ya usa el nombre

    def _ensure_thread(self):
        if self._thread is None:
            from openai_codex import Thread
            from openai_codex.generated.v2_all import (
                ApprovalsReviewer,
                AskForApproval,
                Granular,
                GranularAskForApproval,
                Personality,
                SandboxMode,
                ThreadStartParams,
            )

            # Política granular: solo las apps conectadas (Calendar, Gmail…) pueden pedir aprobación, y esa
            # aprobación la da el usuario (ver _handle_server_request). Todo lo demás se rechaza sin preguntar.
            policy = AskForApproval(root=GranularAskForApproval(granular=Granular(
                mcp_elicitations=True, request_permissions=False, rules=False,
                sandbox_approval=False, skill_approval=False,
            )))
            params = ThreadStartParams(
                approval_policy=policy,
                approvals_reviewer=ApprovalsReviewer.user,
                sandbox=SandboxMode.read_only,
                cwd=str(workspace_dir()),
                developer_instructions=persona_for(self._user_name, self._use_apps),
                personality=Personality.friendly,
                ephemeral=True,
                service_name="robin",
            ).model_dump(by_alias=True, exclude_none=True, mode="json")
            if self._actions is not None:
                params["dynamicTools"] = TOOL_SPECS  # campo experimental del app-server
            started = self._codex._client.thread_start(params)
            self._thread = Thread(self._codex._client, started.thread.id)
        return self._thread

    def _handle_server_request(self, method: str, params: dict | None) -> dict:
        """Peticiones del runtime al cliente. Corre en el hilo lector del SDK: debe ser rápido."""
        params = params or {}
        if method == "item/tool/call":
            if self._actions is None:
                return {"contentItems": [{"type": "inputText", "text": "Acciones no disponibles."}],
                        "success": False}
            result = self._actions.run(str(params.get("tool", "")), params.get("arguments"))
            if result.note:
                self.action_performed.emit(result.note)
            return {"contentItems": [{"type": "inputText", "text": result.text}], "success": result.success}
        if method == "mcpServer/elicitation/request":
            if self._confirmer is None:
                return {"action": "decline"}
            return self._confirmer.handle_elicitation(params)
        if method == "item/tool/requestUserInput":
            if self._confirmer is None:
                return {"answers": {}}
            return self._confirmer.handle_user_input(params)
        if method == "item/permissions/requestApproval":
            return {"permissions": {}}  # no se conceden permisos extra
        if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval",
                      "execCommandApproval", "applyPatchApproval"):
            return {"decision": "decline"}
        log.info("Petición del runtime no atendida: %s", method)
        return {}

    @Slot(str)
    def send(self, text: str) -> None:
        if self._codex is None:
            self.reply_failed.emit("La conexión con ChatGPT no está lista.")
            return
        from openai_codex.generated.v2_all import ReasoningEffort

        self._set_state(AIState.BUSY, "")
        self.reply_started.emit()
        parts: list[str] = []
        last_item: str | None = None
        error: str | None = None
        try:
            thread = self._ensure_thread()
            self._turn = thread.turn(text, effort=ReasoningEffort.low)
            for event in self._turn.stream():
                if event.method == "item/agentMessage/delta":
                    chunk = event.payload.delta
                    if last_item is not None and event.payload.item_id != last_item and parts:
                        chunk = "\n\n" + chunk
                    last_item = event.payload.item_id
                    parts.append(chunk)
                    self.reply_delta.emit(chunk)
                elif event.method == "error" and not getattr(event.payload, "will_retry", False):
                    error = event.payload.error.message
                elif event.method == "turn/completed":
                    turn = event.payload.turn
                    status = getattr(turn.status, "value", turn.status)
                    if status == "failed" and error is None:
                        error = turn.error.message if turn.error else "La respuesta falló."
        except Exception as exc:
            log.exception("Fallo durante el turno")
            error = str(exc)
            self._thread = None
        finally:
            self._turn = None

        if error:
            self.reply_failed.emit(error)
        else:
            self.reply_finished.emit("".join(parts))
        self._set_state(AIState.READY, "")

    def interrupt(self) -> None:
        """Seguro de llamar desde otro hilo: pide cortar la respuesta en curso."""
        turn = self._turn
        if turn is not None:
            try:
                turn.interrupt()
            except Exception:
                log.exception("No se pudo interrumpir el turno")

    # --- utilidades ------------------------------------------------------------

    def _set_state(self, state: AIState, message: str) -> None:
        log.info("Estado IA: %s", state.value)
        self.state_changed.emit(state.value, message)
