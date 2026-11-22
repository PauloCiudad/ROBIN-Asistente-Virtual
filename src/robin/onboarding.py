"""Configuración inicial (tras conectar ChatGPT): ROBIN pregunta el nombre y aprende la voz del usuario.

Aprender la voz significa dos cosas, ambas locales:
  1. Variantes personales: cómo transcribe Whisper tu "Robin" (p. ej. "Rubén") para reconocerlo igual.
  2. Huella de voz (CAM++): para que "Oye Robin" solo funcione con tu voz (switch "Solo responder a mi voz").
Las muestras se guardan en %APPDATA%\\ROBIN\\voice\\samples (base para un detector propio en el futuro).
"""

from __future__ import annotations

import difflib
import logging
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from robin.actions.text_match import normalize
from robin.config import Settings
from robin.voice.speaker import SpeakerProfile, save_samples
from robin.voice.stt import extract_name, find_wake, set_personal_variants, wake_variant_from

log = logging.getLogger(__name__)

# (etiqueta, frase, contiene "Oye Robin")
PHRASES: list[tuple[str, str, bool]] = [
    ("oye_robin_1", "Oye Robin", True),
    ("oye_robin_2", "Oye Robin", True),
    ("oye_robin_3", "Oye Robin", True),
    ("navegador", "Oye Robin, abre el navegador", True),
    ("agenda", "¿Qué tengo hoy en mi agenda?", False),
    ("musica", "Oye Robin, pon música en YouTube", True),
]
_MAX_ATTEMPTS = 3


class OnboardingController(QObject):
    finished = Signal()
    user_named = Signal(str)
    _enroll_done = Signal(str)  # "" = bien; si no, mensaje de error

    def __init__(self, window, listener, tts, speaker: SpeakerProfile, settings: Settings,
                 save_settings: Callable[[], None]) -> None:
        super().__init__(window)
        self._w = window
        self._page = window.onboarding
        self._listener = listener
        self._tts = tts
        self._speaker = speaker
        self._settings = settings
        self._save_settings = save_settings
        self.active = False
        self._step = "idle"
        self._index = 0
        self._attempts = 0
        self._samples: list[tuple[str, object, str, bool]] = []  # (etiqueta, audio, texto tiny, es_wake)
        self._after_speech: Callable[[], None] | None = None
        self._speech_token = 0
        self._voice_ready = False

        self._page.primary_clicked.connect(self._on_primary)
        self._page.secondary_clicked.connect(self._on_secondary)
        self._page.skip_clicked.connect(self._on_skip)
        listener.sample_recorded.connect(self._on_sample)
        listener.level_changed.connect(lambda v: self.active and self._page.set_level(v))
        listener.listening_changed.connect(self._on_listening)
        listener.ready_changed.connect(self._on_voice_ready)
        tts.speaking_changed.connect(self._on_speaking)
        self._enroll_done.connect(self._on_enrolled)

    # --- inicio / fin --------------------------------------------------------------

    def start(self, ask_name: bool = True) -> None:
        self.active = True
        self._listener.set_wake_enabled(False)  # que "Oye Robin" no salte durante el entrenamiento
        self._w.begin_onboarding()
        if ask_name:
            self._step_name()
        else:
            self._step_voice_intro()

    def _finish(self) -> None:
        self.active = False
        self._step = "idle"
        self._settings.onboarding_done = True
        self._save_settings()
        self._listener.set_wake_enabled(self._settings.wake_word_enabled)
        self._w.end_onboarding()
        self.finished.emit()

    # --- utilidades ------------------------------------------------------------------

    def _say_then(self, text: str, then: Callable[[], None] | None = None) -> None:
        """Habla y, al terminar, ejecuta `then` (para no grabar la propia voz de ROBIN)."""
        self._after_speech = then
        self._speech_token += 1
        token = self._speech_token
        if self._settings.voice_enabled:
            self._tts.speak(text)
            # Por si la voz falla (sin internet) y nunca llega el "terminó de hablar".
            QTimer.singleShot(15000, lambda: self._run_after_speech(token))
        else:
            QTimer.singleShot(300, lambda: self._run_after_speech(token))

    def _on_speaking(self, speaking: bool) -> None:
        if not speaking and self.active:
            token = self._speech_token
            QTimer.singleShot(350, lambda: self._run_after_speech(token))

    def _run_after_speech(self, token: int) -> None:
        if token != self._speech_token:
            return  # pertenece a una frase anterior
        callback, self._after_speech = self._after_speech, None
        if callback is not None and self.active:
            callback()

    def _record(self) -> None:
        if not self._voice_ready:
            self._page.set_status("Preparando el micrófono… un momento.", "warn")
            QTimer.singleShot(1500, self._record)
            return
        self._listener.record_sample()

    def _on_voice_ready(self, ready: bool) -> None:
        self._voice_ready = ready

    def _on_listening(self, listening: bool) -> None:
        if self.active and listening:
            self._page.set_status("Te escucho…", "listen")

    # --- paso 1: nombre ------------------------------------------------------------

    def _step_name(self) -> None:
        self._step = "name"
        self._page.show_step(
            "Paso 1 de 2 · Conozcámonos", "Para hablarte por tu nombre", "¿Cómo te llamas?",
            name_field=True, primary="Continuar", secondary="Decirlo por voz", can_skip=False,
        )
        self._say_then("¡Hola! Soy ROBIN, tu nueva asistente. ¿Cómo te llamas?", self._record)

    def _save_name(self) -> None:
        name = self._page.name()
        if not name:
            self._page.set_status("Escribe tu nombre o dímelo por voz.", "warn")
            return
        self._listener.cancel()
        self._settings.user_name = name
        self._save_settings()
        self.user_named.emit(name)
        self._step_voice_intro()

    # --- paso 2: voz ---------------------------------------------------------------

    def _step_voice_intro(self) -> None:
        self._step = "voice_intro"
        self._samples = []
        name = self._settings.user_name
        greeting = f"¡Encantada, {name}!" if name else "¡Vamos con tu voz!"
        self._page.show_step(
            "Paso 2 de 2 · Tu voz", "Voy a aprender cómo suenas. Repite cada frase en voz alta, a tu ritmo normal.",
            greeting, primary="Empezar", can_skip=True,
        )
        self._say_then(f"{greeting} Ahora voy a aprender tu voz. Repite cada frase que aparezca en pantalla.")

    def _step_phrase(self, index: int) -> None:
        self._step = "phrase"
        self._index = index
        self._attempts = 0
        _, text, _ = PHRASES[index]
        self._page.show_step(
            f"Frase {index + 1} de {len(PHRASES)}", "Repite en voz alta:", f"«{text}»",
            secondary="Grabar de nuevo", can_skip=True,
        )
        QTimer.singleShot(400, self._record)

    def _phrase_ok(self, tiny_text: str, base_text: str) -> bool:
        _, text, is_wake = PHRASES[self._index]
        if is_wake:
            return find_wake(tiny_text)[0] or wake_variant_from(tiny_text) is not None
        ratio = difflib.SequenceMatcher(None, normalize(base_text), normalize(text)).ratio()
        return ratio >= 0.5

    # --- eventos -----------------------------------------------------------------------

    @Slot(object, str, str)
    def _on_sample(self, audio, tiny_text: str, base_text: str) -> None:
        if not self.active:
            return
        if self._step == "name":
            if audio is None:
                self._page.set_status("No te escuché. Escribe tu nombre o pulsa «Decirlo por voz».", "warn")
                return
            name = extract_name(base_text)
            self._page.set_name(name)
            self._page.set_status("¿Es correcto? Corrígelo si hace falta y pulsa Continuar.", "info")
            return
        if self._step != "phrase":
            return
        self._attempts += 1
        if audio is None:
            self._page.set_status("No te escuché. Pulsa «Grabar de nuevo» cuando estés listo.", "warn")
            return
        label, _, is_wake = PHRASES[self._index]
        ok = self._phrase_ok(tiny_text, base_text)
        if not ok and self._attempts < _MAX_ATTEMPTS:
            self._page.set_status("No te entendí bien. Repítelo otra vez, por favor.", "warn")
            QTimer.singleShot(900, self._record)
            return
        self._samples.append((label, audio, tiny_text, is_wake))
        self._page.set_status("¡Perfecto!" if ok else "Listo, sigamos.", "ok")
        nxt = self._index + 1
        QTimer.singleShot(700, (lambda: self._step_phrase(nxt)) if nxt < len(PHRASES) else self._step_learn)

    def _on_primary(self) -> None:
        if self._step == "name":
            self._save_name()
        elif self._step == "voice_intro":
            self._after_speech = None
            self._tts.stop()
            self._step_phrase(0)
        elif self._step == "done":
            self._finish()

    def _on_secondary(self) -> None:
        if self._step == "name":
            self._after_speech = None  # evita una segunda grabación al terminar de hablar
            self._tts.stop()
            self._record()
        elif self._step == "phrase":
            self._listener.cancel()
            self._attempts = 0
            QTimer.singleShot(300, self._record)

    def _on_skip(self) -> None:
        self._listener.cancel()
        self._tts.stop()
        self._after_speech = None
        self._finish()

    # --- aprendizaje -----------------------------------------------------------------

    def _step_learn(self) -> None:
        self._step = "learning"
        self._page.show_step("Casi listo", "Estoy aprendiendo tu voz…", "Un momento", can_skip=False)
        samples = list(self._samples)
        threading.Thread(target=self._learn, args=(samples,), name="robin-enroll", daemon=True).start()

    def _learn(self, samples) -> None:
        try:
            variants = {v for _, _, t, is_wake in samples if is_wake and (v := wake_variant_from(t))}
            self._speaker.enroll([a for _, a, _, _ in samples], variants)
            set_personal_variants(variants)
            save_samples([(label, audio) for label, audio, _, _ in samples])
            self._enroll_done.emit("")
        except Exception as exc:
            log.exception("No se pudo crear el perfil de voz")
            self._enroll_done.emit(str(exc))

    def _on_enrolled(self, error: str) -> None:
        self._step = "done"
        name = self._settings.user_name
        if error:
            self._page.show_step("Listo", f"No pude guardar tu huella de voz ({error}), pero ya puedes usarme.",
                                 "¡Todo listo!", primary="Empezar", can_skip=False)
        else:
            self._page.show_step("Listo", "Ya conozco tu voz. Di «Oye Robin» o pulsa Alt + X cuando me necesites.",
                                 f"¡Todo listo{', ' + name if name else ''}!", primary="Empezar", can_skip=False)
        self._say_then(f"¡Listo{', ' + name if name else ''}! Ya conozco tu voz. "
                       "Cuando me necesites, di Oye Robin o pulsa Alt más X.")
