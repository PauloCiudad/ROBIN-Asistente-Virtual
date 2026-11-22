"""Arranque de ROBIN: une bandeja, atajo global, ventana y servicio de IA."""

from __future__ import annotations

import ctypes
import logging

from PySide6.QtCore import QMetaObject, QObject, QThread, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from robin import APP_NAME, autostart
from robin.actions.tools import ActionRunner
from robin.ai.chatgpt import ChatGPTService
from robin.ai.confirm import ConfirmationBroker, parse_yes_no
from robin.config import Settings, setup_logging
from robin.hotkey import MOD_ALT, GlobalHotkey
from robin.learning.activity import ActivityLog
from robin.learning.automations import AutomationStore, open_folder
from robin.learning.observers import AppObserver, FileObserver
from robin.learning.watcher import PatternWatcher
from robin.onboarding import OnboardingController
from robin.single_instance import InstanceServer, notify_running_instance
from robin.ui.widgets import robin_icon
from robin.ui.window import RobinWindow
from robin.voice.chime import play_chime
from robin.voice.listener import VoiceListener
from robin.voice.speaker import SpeakerProfile
from robin.voice.stt import set_personal_variants
from robin.voice.text import SentenceSplitter
from robin.voice.tts import TextToSpeech

log = logging.getLogger(__name__)

VK_X = 0x58


class RobinController(QObject):
    user_name_set = Signal(str)
    use_apps_set = Signal(bool)

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self.settings = Settings.load()
        if self.settings.start_with_windows:
            autostart.set_enabled(True)  # refresca la ruta por si cambió el entorno

        self.window = RobinWindow(self.settings)
        self.window.setting_changed.connect(self._on_setting_changed)
        self.window.name_changed.connect(self._on_name_changed)
        self._voice_ready = False

        self._instance_server = InstanceServer(self)
        self._instance_server.show_requested.connect(self.window.show_window)

        self.hotkey = GlobalHotkey(MOD_ALT, VK_X, self)
        self.hotkey.activated.connect(self._on_hotkey)

        self._build_tray()
        self._start_voice()
        self._start_listener()
        self._start_ai()
        self._start_onboarding()
        self._start_learning()

        if self.hotkey.registered:
            hello = "Di “Oye Robin” o pulsa Alt + X" if self.settings.wake_word_enabled else "Pulsa Alt + X"
            self.tray.showMessage(APP_NAME, f"Estoy lista. {hello} cuando me necesites.", robin_icon(), 4000)
        else:
            self.tray.showMessage(
                APP_NAME,
                "Otra aplicación está usando Alt + X. Ábreme desde el icono de la bandeja.",
                QSystemTrayIcon.Warning,
                6000,
            )
        app.aboutToQuit.connect(self._shutdown)

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(robin_icon(), self)
        self.tray.setToolTip(f"{APP_NAME} — Alt + X")
        menu = QMenu()
        act_open = QAction("Abrir ROBIN\tAlt+X", menu)
        act_open.triggered.connect(self.window.show_window)
        act_settings = QAction("Ajustes", menu)
        act_settings.triggered.connect(self.window.show_settings)
        act_quit = QAction("Salir", menu)
        act_quit.triggered.connect(self._app.quit)
        menu.addAction(act_open)
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)
        self._menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self._on_hotkey()

    def _on_hotkey(self) -> None:
        """Alt + X (o clic en la bandeja): si está abierta, se oculta; si no, se abre ya escuchando."""
        if self.window.isVisible():
            self.window.dismiss()
            return
        self.window.show_window()
        if self._voice_ready and self.window.ai_ready and not self.onboarding.active:
            self._on_mic_requested()

    def _start_voice(self) -> None:
        self.tts = TextToSpeech(self.settings.tts_voice, self)
        self.tts.speaking_changed.connect(self.window.set_speaking)
        self.tts.failed.connect(self._on_tts_failed)
        self._splitter: SentenceSplitter | None = None
        self._tts_error_shown = False

    def _start_listener(self) -> None:
        self.speaker = SpeakerProfile()
        set_personal_variants(self.speaker.wake_variants)
        self.listener = VoiceListener(self.speaker, self)
        self.listener.owner_only = self.settings.owner_voice_only
        w = self.window
        self.listener.ready_changed.connect(w.set_voice_ready)
        self.listener.ready_changed.connect(lambda ready: setattr(self, "_voice_ready", ready))
        self.listener.wake_detected.connect(self._on_wake)
        self.listener.listening_changed.connect(w.set_listening)
        self.listener.transcribing_changed.connect(w.set_transcribing)
        self.listener.command_recognized.connect(self._on_command)
        self.listener.failed.connect(self._on_listener_failed)
        # Mientras ROBIN habla, solo "Oye Robin" completo la activa (su propia voz no debe despertarla).
        self.tts.speaking_changed.connect(self.listener.set_strict)
        w.mic_requested.connect(self._on_mic_requested)
        w.mic_cancel_requested.connect(self.listener.cancel)
        self.listener.set_wake_enabled(self.settings.wake_word_enabled)

    def _on_wake(self) -> None:
        if self.onboarding.active:
            return
        self.tts.stop()
        play_chime()
        self.window.show_window()

    def _on_command(self, text: str) -> None:
        if self.onboarding.active:
            return
        if self.confirmer.pending:
            self._on_confirmation_voice(text)
            return
        self.window.submit_voice_text(text)

    # --- confirmación de acciones de apps conectadas ------------------------------

    def _on_confirmation_requested(self, text: str) -> None:
        self._confirm_retries = 0
        if self._splitter is not None:  # lo que ROBIN ya explicó ("Voy a crear…") se dice antes de preguntar
            for sentence in self._splitter.flush():
                self.tts.speak(sentence)
        self.window.show_window()
        self.window.show_confirmation(text)
        self._ask_confirmation("Antes de hacerlo necesito tu permiso. ¿Lo confirmo?")

    def _ask_confirmation(self, question: str) -> None:
        if self.settings.voice_enabled:
            self._listen_after_speech = True
            self.tts.speak(question)
        else:
            self._listen_for_confirmation()

    def _on_speaking_done(self, speaking: bool) -> None:
        if not speaking and self._listen_after_speech:
            self._listen_after_speech = False
            self._listen_for_confirmation()

    def _listen_for_confirmation(self) -> None:
        if self.confirmer.pending and self._voice_ready:
            play_chime()
            self.listener.start_command()

    def _on_confirmation_voice(self, text: str) -> None:
        decision = parse_yes_no(text)
        if decision is not None:
            self.confirmer.resolve(decision)
            return
        self._confirm_retries += 1
        if self._confirm_retries <= 2:
            self._ask_confirmation("No te entendí. ¿Sí o no?")

    def _on_confirmation_finished(self, accepted: bool) -> None:
        self._listen_after_speech = False
        self.window.hide_confirmation()
        self.window.add_note("Permiso concedido" if accepted else "Acción cancelada")
        self.listener.cancel()

    def _start_onboarding(self) -> None:
        self.onboarding = OnboardingController(
            self.window, self.listener, self.tts, self.speaker, self.settings, self.settings.save
        )
        self.onboarding.user_named.connect(self._on_name_changed)
        self.window.retrain_requested.connect(lambda: self.onboarding.start(ask_name=False))
        # La primera vez que la IA queda lista (cuenta de ChatGPT conectada), empieza la configuración.
        self.ai.state_changed.connect(self._maybe_start_onboarding)

    def _maybe_start_onboarding(self, state: str, _message: str) -> None:
        if state == "ready" and not self.settings.onboarding_done and not self.onboarding.active:
            self.onboarding.start(ask_name=not self.settings.user_name)

    def _on_name_changed(self, name: str) -> None:
        self.settings.user_name = name
        self.settings.save()
        self.window.set_user_name(name)
        self.user_name_set.emit(name)  # llega al hilo de la IA en cola

    def _on_mic_requested(self) -> None:
        self.tts.stop()
        play_chime()
        self.listener.start_command()

    def _on_listener_failed(self, message: str) -> None:
        self.tray.showMessage(APP_NAME, message, QSystemTrayIcon.Warning, 5000)

    def _on_reply_started(self) -> None:
        self.tts.stop()
        self._splitter = SentenceSplitter() if self.settings.voice_enabled else None

    def _on_reply_delta(self, delta: str) -> None:
        if self._splitter is not None:
            for sentence in self._splitter.feed(delta):
                self.tts.speak(sentence)

    def _on_reply_finished(self, _text: str) -> None:
        if self._splitter is not None:
            for sentence in self._splitter.flush():
                self.tts.speak(sentence)
        self._splitter = None

    def _on_tts_failed(self, message: str) -> None:
        if not self._tts_error_shown:  # un aviso por sesión basta
            self._tts_error_shown = True
            self.tray.showMessage(APP_NAME, message, QSystemTrayIcon.Warning, 5000)

    def _stop_everything(self) -> None:
        """Botón Detener: corta la respuesta en curso y la voz. Se ejecuta en el hilo de la UI."""
        self.ai.interrupt()
        self.tts.stop()
        self._splitter = None

    def _start_ai(self) -> None:
        self._ai_thread = QThread(self)
        self._ai_thread.setObjectName("robin-ai")
        self.confirmer = ConfirmationBroker(self)
        self.activity = ActivityLog()
        self.automations = AutomationStore()
        self.actions = ActionRunner(
            is_allowed=lambda: self.settings.allow_open_apps,
            on_action=self._record_action,
            automations=self.automations,
            confirm=lambda question: self.confirmer.ask(question),  # bloquea el hilo lector hasta responder
        )
        self._listen_after_speech = False
        self._confirm_retries = 0
        self.confirmer.requested.connect(self._on_confirmation_requested)
        self.confirmer.finished.connect(self._on_confirmation_finished)
        self.window.confirm_answered.connect(self.confirmer.resolve)
        self.tts.speaking_changed.connect(self._on_speaking_done)
        self.ai = ChatGPTService(self.actions, self.settings.user_name, confirmer=self.confirmer,
                                 use_apps=self.settings.use_chatgpt_apps)
        self.ai.moveToThread(self._ai_thread)
        self._ai_thread.started.connect(self.ai.start)

        w = self.window
        # De la IA a la ventana (cola automática al hilo de la interfaz).
        self.ai.state_changed.connect(w.set_state)
        self.ai.account_changed.connect(w.set_account)
        self.ai.reply_started.connect(w.on_reply_started)
        self.ai.reply_delta.connect(w.on_reply_delta)
        self.ai.reply_finished.connect(w.on_reply_finished)
        self.ai.reply_failed.connect(w.on_reply_failed)
        self.ai.action_performed.connect(w.add_note)
        # Voz: frases completas a TTS mientras llega el texto.
        self.ai.reply_started.connect(self._on_reply_started)
        self.ai.reply_delta.connect(self._on_reply_delta)
        self.ai.reply_finished.connect(self._on_reply_finished)
        self.ai.reply_failed.connect(lambda _e: setattr(self, "_splitter", None))
        # De la ventana a la IA (se ejecutan en el hilo de la IA).
        w.send_requested.connect(self.ai.send)
        self.user_name_set.connect(self.ai.set_user_name)
        self.use_apps_set.connect(self.ai.set_use_apps)
        w.login_requested.connect(self.ai.login)
        w.logout_requested.connect(self.ai.logout)
        w.retry_requested.connect(self.ai.start)
        # Sin historial: al ocultar la ventana, la próxima vez empieza una conversación nueva.
        w.hidden.connect(self.ai.new_conversation)
        # Estas dos deben ejecutarse ya, aunque el hilo de la IA esté ocupado esperando.
        w.stop_requested.connect(self._stop_everything, Qt.DirectConnection)
        w.cancel_login_requested.connect(lambda: self.ai.cancel_login(), Qt.DirectConnection)

        self._ai_thread.start()

    # --- aprendizaje de rutinas (Fase 3) ---------------------------------------------

    def _start_learning(self) -> None:
        self._app_observer = AppObserver(self.activity, lambda: self.settings.observe_apps, self)
        self._file_observer = FileObserver(self.activity, lambda: self.settings.observe_files, self)
        self.watcher = PatternWatcher(self.activity, self.automations, self)
        self.watcher.suggestion.connect(self._on_suggestion)
        w = self.window
        w.suggestion_answered.connect(self._on_suggestion_answered)
        w.open_automations_requested.connect(lambda: open_folder(self.automations.folder))
        w.scan_patterns_requested.connect(self._scan_now)
        w.clear_learning_requested.connect(self._clear_learning)
        self._refresh_learning_info()

    def _record_action(self, kind: str, label: str, meta: dict) -> None:
        if self.settings.observe_requests:
            self.activity.record("action", kind, label, meta)

    def _refresh_learning_info(self) -> None:
        self.window.set_automation_count(len(self.automations.list()), self.activity.count())

    def _on_suggestion(self, pattern) -> None:
        self.window.show_suggestion(pattern.title, pattern.description)
        self.tray.showMessage(APP_NAME, f"Noté una rutina: {pattern.title}. Ábreme para verla.", robin_icon(), 6000)

    def _on_suggestion_answered(self, choice: str) -> None:
        self.window.hide_suggestion()
        automation = self.watcher.answer(choice)
        if automation is not None:
            self.window.add_note(f"Automatización creada: {automation.name}")
            if self.settings.voice_enabled:
                self.tts.speak(f"Listo, creé la automatización {automation.name}. "
                               f"Cuando quieras, dime: {automation.trigger}.")
        self._refresh_learning_info()

    def _scan_now(self) -> None:
        found = self.watcher.scan()
        self._refresh_learning_info()
        if found:
            self.window.dismiss()
            self.window.show_window()  # la sugerencia aparece en la vista principal
        else:
            self.tray.showMessage(APP_NAME, "Aún no encontré rutinas nuevas. Necesito ver la misma rutina al "
                                  "menos 3 días.", robin_icon(), 5000)

    def _clear_learning(self) -> None:
        self.activity.clear()
        self.automations.reset_suggestions()
        self._refresh_learning_info()
        self.tray.showMessage(APP_NAME, "Borré todo lo que había aprendido de tu actividad.", robin_icon(), 4000)

    def _on_setting_changed(self, key: str, value: bool) -> None:
        setattr(self.settings, key, value)
        self.settings.save()
        log.info("Ajuste %s = %s", key, value)
        if key == "start_with_windows":
            autostart.set_enabled(value)
        elif key == "voice_enabled" and not value:
            self.tts.stop()
            self._splitter = None
        elif key == "wake_word_enabled" and not self.onboarding.active:
            self.listener.set_wake_enabled(value)
        elif key == "owner_voice_only":
            self.listener.owner_only = value
        elif key == "use_chatgpt_apps":
            self.use_apps_set.emit(value)

    def _shutdown(self) -> None:
        log.info("Cerrando ROBIN")
        self.hotkey.unregister()
        self.tray.hide()
        self.listener.shutdown()
        self.tts.shutdown()
        self.confirmer.resolve(False)  # desbloquea un permiso pendiente
        self.activity.close()
        self.ai.cancel_login()
        self.ai.interrupt()
        # shutdown() cierra Codex y termina el hilo; si se quedó colgado, se fuerza la salida del bucle.
        QMetaObject.invokeMethod(self.ai, "shutdown", Qt.QueuedConnection)
        if not self._ai_thread.wait(5000):
            log.warning("El hilo de IA no terminó a tiempo")
            self._ai_thread.quit()
            self._ai_thread.wait(1000)


def run(argv: list[str]) -> int:
    # Identidad propia en Windows (notificaciones y barra de tareas muestran ROBIN, no Python).
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_NAME)
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    if notify_running_instance():
        return 0
    setup_logging()
    log.info("Iniciando ROBIN")
    controller = RobinController(app)  # noqa: F841 — debe vivir mientras corre la app
    return app.exec()
