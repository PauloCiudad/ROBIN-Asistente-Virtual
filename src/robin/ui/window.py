"""Ventana de ROBIN: pequeña, flotante, abajo a la izquierda y con estilo glass.

No es un chat: muestra solo lo último que dijo el usuario y la respuesta actual.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from robin.ai.chatgpt import AIState
from robin.config import Settings
from robin.ui.glass import apply_glass
from robin.ui.onboarding import OnboardingPage
from robin.ui.widgets import ToggleSwitch, robin_icon

ICON_SETTINGS, ICON_CLOSE, ICON_BACK, ICON_SEND, ICON_STOP = "", "", "", "", ""
ICON_VOLUME, ICON_MUTE, ICON_MIC = "", "", ""

# (clave en Settings, título, descripción, disponible ya)
SETTINGS_SECTIONS: list[tuple[str, list[tuple[str, str, str, bool]]]] = [
    ("General", [
        ("start_with_windows", "Iniciar con Windows", "ROBIN se queda en la bandeja al encender el PC.", True),
    ]),
    ("Voz", [
        ("voice_enabled", "Voz de ROBIN", "Lee las respuestas en voz alta, con acento peruano.", True),
        ("wake_word_enabled", "Escuchar “Oye Robin”", "Todo se procesa en tu PC: no se envía audio a internet.", True),
        ("owner_voice_only", "Solo responder a mi voz", "“Oye Robin” solo funciona con tu voz entrenada.", True),
    ]),
    ("Acciones", [
        ("allow_open_apps", "Abrir apps, archivos y webs", "ROBIN puede abrir cosas en tu PC cuando se lo pidas.", True),
        ("use_chatgpt_apps", "Usar mis apps de ChatGPT",
         "Google Calendar, Gmail y demás apps conectadas en tu ChatGPT. Siempre te pide permiso antes de "
         "crear, cambiar, borrar o enviar algo.", True),
    ]),
    ("Aprendizaje de patrones", [
        ("observe_requests", "Lo que le pido a ROBIN", "Aprende qué acciones le pides juntas a ROBIN.", True),
        ("observe_apps", "Apps que uso", "Qué programas abres y cuándo (nunca el contenido ni títulos).", True),
        ("observe_files", "Archivos que abro", "Documentos que abres seguido (según Recientes de Windows).", True),
        ("observe_keyboard", "Teclado", "Atajos y textos que repites. Todo se queda en tu PC.", False),
    ]),
]

STATUS_TEXT = {
    AIState.STARTING: ("Conectando…", "#F5C451"),
    AIState.NEEDS_LOGIN: ("Sin sesión", "#F5C451"),
    AIState.LOGGING_IN: ("Iniciando sesión…", "#F5C451"),
    AIState.READY: ("Lista", "#4ADE80"),
    AIState.BUSY: ("Pensando…", "#8B7CFF"),
    AIState.ERROR: ("Error", "#F87171"),
}

STYLE = """
QWidget { color: #F2F3F7; font-family: 'Segoe UI Variable Text', 'Segoe UI'; font-size: 10pt; }
QLabel#title { font-size: 12pt; font-weight: 600; }
QLabel#status, QLabel#hint, QLabel#desc { color: rgba(242,243,247,0.62); font-size: 8.5pt; }
QLabel#section { color: rgba(242,243,247,0.55); font-size: 8.5pt; font-weight: 600; padding-top: 10px; }
QLabel#soon { color: #C9C2FF; background: rgba(139,124,255,0.22); border-radius: 6px;
              padding: 1px 6px; font-size: 7.5pt; }
QLabel#bigtitle { font-size: 14pt; font-weight: 600; }
QLabel#greeting { font-size: 15pt; font-weight: 600; }
QLabel#you { color: rgba(242,243,247,0.70); font-style: italic; }
QLabel#reply { font-size: 11pt; }
QLabel#replyError { font-size: 10pt; color: #FCA5A5; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 6px; margin: 2px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.18); border-radius: 3px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page { background: none; height: 0; }
QPushButton#icon { font-family: 'Segoe Fluent Icons', 'Segoe MDL2 Assets'; font-size: 10pt; background: transparent;
                   border: none; border-radius: 8px; min-width: 30px; min-height: 30px; }
QPushButton#icon:hover { background: rgba(255,255,255,0.10); }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #8B7CFF, stop:1 #4FD1FF);
                      color: white; border: none; border-radius: 12px; padding: 10px 18px; font-weight: 600; }
QPushButton#primary:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #9A8DFF, stop:1 #6BDAFF); }
QPushButton#secondary { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.14);
                        border-radius: 10px; padding: 8px 14px; }
QPushButton#secondary:hover { background: rgba(255,255,255,0.14); }
QPushButton#link { background: transparent; border: none; color: rgba(242,243,247,0.55); font-size: 8.5pt; }
QPushButton#link:hover { color: #F2F3F7; text-decoration: underline; }
QPushButton#send { font-family: 'Segoe Fluent Icons', 'Segoe MDL2 Assets'; color: white; border: none;
                   border-radius: 17px; min-width: 34px; min-height: 34px;
                   background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #8B7CFF, stop:1 #4FD1FF); }
QPushButton#send:disabled { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.4); }
QPushButton#mic { font-family: 'Segoe Fluent Icons', 'Segoe MDL2 Assets'; color: white; border-radius: 17px;
                  min-width: 34px; min-height: 34px; background: rgba(255,255,255,0.10);
                  border: 1px solid rgba(255,255,255,0.14); }
QPushButton#mic:hover { background: rgba(255,255,255,0.18); }
QPushButton#mic:disabled { color: rgba(255,255,255,0.3); }
QPushButton#mic[listening="true"] { background: #F87171; border: 1px solid #FCA5A5; }
QLineEdit { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: 17px;
            padding: 7px 14px; selection-background-color: #8B7CFF; }
QLineEdit:focus { border: 1px solid rgba(139,124,255,0.75); }
QFrame#row { background: rgba(255,255,255,0.05); border-radius: 12px; }
QLabel#note { color: #BFE9FF; background: rgba(79,209,255,0.14); border-radius: 10px; padding: 3px 10px;
              font-size: 8.5pt; }
QFrame#suggest { background: rgba(79,209,255,0.10); border: 1px solid rgba(79,209,255,0.40); border-radius: 12px; }
QLabel#suggestTitle { color: #BFE9FF; font-weight: 600; }
QFrame#confirm { background: rgba(245,196,81,0.12); border: 1px solid rgba(245,196,81,0.45); border-radius: 12px; }
QLabel#confirmTitle { color: #F5C451; font-weight: 600; }
QProgressBar#level { background: rgba(255,255,255,0.10); border: none; border-radius: 3px; }
QProgressBar#level::chunk { border-radius: 3px;
                            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8B7CFF, stop:1 #4FD1FF); }
"""


def _icon_button(glyph: str, tooltip: str) -> QPushButton:
    btn = QPushButton(glyph)
    btn.setObjectName("icon")
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFocusPolicy(Qt.NoFocus)
    return btn


def _restyle(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class RobinWindow(QWidget):
    send_requested = Signal(str)
    stop_requested = Signal()
    mic_requested = Signal()
    mic_cancel_requested = Signal()
    login_requested = Signal()
    cancel_login_requested = Signal()
    logout_requested = Signal()
    retry_requested = Signal()
    setting_changed = Signal(str, bool)
    name_changed = Signal(str)
    retrain_requested = Signal()
    confirm_answered = Signal(bool)
    suggestion_answered = Signal(str)  # "create" | "later" | "never"
    open_automations_requested = Signal()
    scan_patterns_requested = Signal()
    clear_learning_requested = Signal()
    hidden = Signal()

    WIDTH, HEIGHT, RADIUS = 420, 440, 16

    def __init__(self, settings: Settings) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("ROBIN")
        self.setWindowIcon(robin_icon())
        self.resize(self.WIDTH, self.HEIGHT)
        self.setStyleSheet(STYLE)
        self._settings = settings
        self._switches: dict[str, ToggleSwitch] = {}
        self._glass_applied = False
        self._state = AIState.STARTING
        self._speaking = self._listening = self._transcribing = False
        self._confirming = False
        self._reply_text = ""
        self._reply_active = False
        self.onboarding_active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 14)
        root.setSpacing(8)
        root.addWidget(self._build_header())

        self._stack = QStackedWidget()
        self._assistant_page = self._build_assistant_page()
        self._auth_page = self._build_auth_page()
        self._settings_page = self._build_settings_page()
        self.onboarding = OnboardingPage()
        for page in (self._assistant_page, self._auth_page, self._settings_page, self.onboarding):
            self._stack.addWidget(page)
        root.addWidget(self._stack, 1)

        self._update_voice_button(settings.voice_enabled)
        self.reset_view()
        self.set_state(AIState.STARTING.value, "Conectando con ChatGPT…")

    # --- construcción ---------------------------------------------------------

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(40)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(2, 0, 0, 0)
        lay.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(robin_icon(56).pixmap(24, 24))
        title = QLabel("ROBIN")
        title.setObjectName("title")
        self._dot = QLabel("●")
        self._status = QLabel()
        self._status.setObjectName("status")
        lay.addWidget(logo)
        lay.addWidget(title)
        lay.addSpacing(2)
        lay.addWidget(self._dot)
        lay.addWidget(self._status)
        lay.addStretch(1)
        self._btn_voice = _icon_button(ICON_VOLUME, "")
        self._btn_settings = _icon_button(ICON_SETTINGS, "Ajustes")
        btn_close = _icon_button(ICON_CLOSE, "Ocultar (Esc)")
        self._btn_voice.clicked.connect(lambda: self._switches["voice_enabled"].toggle())
        self._btn_settings.clicked.connect(self._toggle_settings)
        btn_close.clicked.connect(self.dismiss)
        for b in (self._btn_voice, self._btn_settings, btn_close):
            lay.addWidget(b)
        self._header = header
        return header

    def _build_assistant_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 0, 0, 0)
        lay.setSpacing(10)

        self._greeting = QLabel()
        self._greeting.setObjectName("greeting")
        self._greeting.setWordWrap(True)
        self._you = QLabel()
        self._you.setObjectName("you")
        self._you.setWordWrap(True)
        self._notes = QHBoxLayout()
        self._notes.setSpacing(6)
        self._notes.addStretch(1)

        self._reply = QLabel()
        self._reply.setObjectName("reply")
        self._reply.setWordWrap(True)
        self._reply.setTextFormat(Qt.MarkdownText)
        self._reply.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._reply.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self._reply.setOpenExternalLinks(True)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        holder_lay = QVBoxLayout(holder)
        holder_lay.setContentsMargins(0, 0, 6, 0)
        holder_lay.addWidget(self._reply)
        holder_lay.addStretch(1)
        scroll.setWidget(holder)
        bar = scroll.verticalScrollBar()
        bar.rangeChanged.connect(lambda _min, maximum: bar.setValue(maximum))

        lay.addWidget(self._greeting)
        lay.addWidget(self._you)
        lay.addLayout(self._notes)
        lay.addWidget(scroll, 1)
        lay.addWidget(self._build_suggestion_card())
        lay.addWidget(self._build_confirm_card())

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self._btn_mic = QPushButton(ICON_MIC)
        self._btn_mic.setObjectName("mic")
        self._btn_mic.setCursor(Qt.PointingHandCursor)
        self._btn_mic.setEnabled(False)
        self._btn_mic.setToolTip("Preparando el reconocimiento de voz…")
        self._btn_mic.clicked.connect(self._on_mic_clicked)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Escríbele a ROBIN…")
        self._input.returnPressed.connect(self._on_send)
        self._btn_send = QPushButton(ICON_SEND)
        self._btn_send.setObjectName("send")
        self._btn_send.setCursor(Qt.PointingHandCursor)
        self._btn_send.setToolTip("Enviar (Enter)")
        self._btn_send.clicked.connect(self._on_send_clicked)
        input_row.addWidget(self._btn_mic)
        input_row.addWidget(self._input, 1)
        input_row.addWidget(self._btn_send)
        lay.addLayout(input_row)
        hint = QLabel("Di “Oye Robin” o pulsa Alt + X · Esc para ocultar")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignCenter)
        lay.addWidget(hint)
        return page

    def _build_confirm_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("confirm")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)
        title = QLabel("Necesito tu permiso")
        title.setObjectName("confirmTitle")
        self._confirm_text = QLabel()
        self._confirm_text.setWordWrap(True)
        hint = QLabel("Responde «sí» o «no» por voz, o con los botones.")
        hint.setObjectName("desc")
        buttons = QHBoxLayout()
        no = QPushButton("No")
        no.setObjectName("secondary")
        no.setCursor(Qt.PointingHandCursor)
        no.clicked.connect(lambda: self.confirm_answered.emit(False))
        yes = QPushButton("Sí, hazlo")
        yes.setObjectName("primary")
        yes.setCursor(Qt.PointingHandCursor)
        yes.clicked.connect(lambda: self.confirm_answered.emit(True))
        buttons.addWidget(no)
        buttons.addWidget(yes, 1)
        for w in (title, self._confirm_text, hint):
            lay.addWidget(w)
        lay.addLayout(buttons)
        card.hide()
        self._confirm_card = card
        return card

    def _build_suggestion_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("suggest")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 8)
        lay.setSpacing(6)
        self._suggest_title = QLabel()
        self._suggest_title.setObjectName("suggestTitle")
        self._suggest_title.setWordWrap(True)
        self._suggest_text = QLabel()
        self._suggest_text.setWordWrap(True)
        buttons = QHBoxLayout()
        later = QPushButton("Ahora no")
        later.setObjectName("secondary")
        later.setCursor(Qt.PointingHandCursor)
        later.clicked.connect(lambda: self.suggestion_answered.emit("later"))
        create = QPushButton("Crear automatización")
        create.setObjectName("primary")
        create.setCursor(Qt.PointingHandCursor)
        create.clicked.connect(lambda: self.suggestion_answered.emit("create"))
        buttons.addWidget(later)
        buttons.addWidget(create, 1)
        never = QPushButton("No volver a sugerir esta rutina")
        never.setObjectName("link")
        never.setCursor(Qt.PointingHandCursor)
        never.clicked.connect(lambda: self.suggestion_answered.emit("never"))
        lay.addWidget(self._suggest_title)
        lay.addWidget(self._suggest_text)
        lay.addLayout(buttons)
        lay.addWidget(never, 0, Qt.AlignCenter)
        card.hide()
        self._suggest_card = card
        return card

    def show_suggestion(self, title: str, text: str) -> None:
        self._suggest_title.setText(f"💡 Noté una rutina: {title}")
        self._suggest_text.setText(text)
        self._suggest_card.show()

    def hide_suggestion(self) -> None:
        self._suggest_card.hide()

    def set_automation_count(self, count: int, events: int) -> None:
        self._automation_info.setText(
            f"{count} automatización(es) creada(s) · {events} evento(s) aprendido(s) en tu PC."
        )

    def show_confirmation(self, text: str) -> None:
        self._confirming = True
        self._confirm_text.setText(text)
        self._confirm_card.show()
        if self._stack.currentWidget() is not self.onboarding:
            self._stack.setCurrentWidget(self._assistant_page)
        self._refresh_status()

    def hide_confirmation(self) -> None:
        self._confirming = False
        self._confirm_card.hide()
        self._refresh_status()

    def _build_auth_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 0, 18, 16)
        lay.setSpacing(12)
        lay.addStretch(1)
        logo = QLabel()
        logo.setPixmap(robin_icon(128).pixmap(64, 64))
        logo.setAlignment(Qt.AlignCenter)
        self._auth_title = QLabel("Conecta tu cuenta de ChatGPT")
        self._auth_title.setObjectName("bigtitle")
        self._auth_title.setAlignment(Qt.AlignCenter)
        info = QLabel(
            "ROBIN usa tu plan de ChatGPT con el inicio de sesión oficial de OpenAI. "
            "No necesitas API key: se abrirá tu navegador para que inicies sesión."
        )
        info.setObjectName("desc")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignCenter)
        self._auth_message = QLabel()
        self._auth_message.setWordWrap(True)
        self._auth_message.setAlignment(Qt.AlignCenter)
        self._btn_login = QPushButton("Iniciar sesión con ChatGPT")
        self._btn_login.setObjectName("primary")
        self._btn_login.setCursor(Qt.PointingHandCursor)
        self._btn_login.clicked.connect(self._on_auth_primary)
        self._btn_cancel_login = QPushButton("Cancelar")
        self._btn_cancel_login.setObjectName("secondary")
        self._btn_cancel_login.setCursor(Qt.PointingHandCursor)
        self._btn_cancel_login.clicked.connect(self.cancel_login_requested)
        for w in (logo, self._auth_title, info, self._auth_message):
            lay.addWidget(w)
        lay.addSpacing(6)
        lay.addWidget(self._btn_login)
        lay.addWidget(self._btn_cancel_login, 0, Qt.AlignCenter)
        lay.addStretch(2)
        return page

    def _build_settings_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(6)

        lay.addWidget(self._section_label("Tu perfil"))
        row = QFrame()
        row.setObjectName("row")
        rl = QVBoxLayout(row)
        rl.setContentsMargins(12, 10, 12, 10)
        rl.addWidget(QLabel("¿Cómo te llamo?"))
        self._name_input = QLineEdit(self._settings.user_name)
        self._name_input.setPlaceholderText("Tu nombre")
        self._name_input.editingFinished.connect(lambda: self.name_changed.emit(self._name_input.text().strip()))
        rl.addWidget(self._name_input)
        retrain = QPushButton("Volver a entrenar mi voz")
        retrain.setObjectName("secondary")
        retrain.setCursor(Qt.PointingHandCursor)
        retrain.clicked.connect(self.retrain_requested)
        rl.addWidget(retrain, 0, Qt.AlignLeft)
        lay.addWidget(row)

        for section, items in SETTINGS_SECTIONS:
            lay.addWidget(self._section_label(section))
            for key, title, desc, available in items:
                lay.addWidget(self._setting_row(key, title, desc, available))

        lay.addWidget(self._section_label("Automatizaciones"))
        row = QFrame()
        row.setObjectName("row")
        rl = QVBoxLayout(row)
        rl.setContentsMargins(12, 10, 12, 10)
        self._automation_info = QLabel("0 automatizaciones")
        self._automation_info.setObjectName("desc")
        self._automation_info.setWordWrap(True)
        rl.addWidget(self._automation_info)
        rows = [(("Abrir carpeta", self.open_automations_requested),
                 ("Buscar rutinas ahora", self.scan_patterns_requested)),
                (("Borrar lo aprendido", self.clear_learning_requested),)]
        for row_items in rows:
            buttons = QHBoxLayout()
            for text, signal in row_items:
                btn = QPushButton(text)
                btn.setObjectName("secondary")
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(signal)
                buttons.addWidget(btn)
            buttons.addStretch(1)
            rl.addLayout(buttons)
        lay.addWidget(row)

        lay.addWidget(self._section_label("Cuenta"))
        row = QFrame()
        row.setObjectName("row")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 10, 12, 10)
        self._account_label = QLabel("Sin sesión")
        self._account_label.setWordWrap(True)
        self._btn_logout = QPushButton("Cerrar sesión")
        self._btn_logout.setObjectName("secondary")
        self._btn_logout.setCursor(Qt.PointingHandCursor)
        self._btn_logout.clicked.connect(self.logout_requested)
        rl.addWidget(self._account_label, 1)
        rl.addWidget(self._btn_logout)
        lay.addWidget(row)
        lay.addStretch(1)
        scroll.setWidget(container)
        return scroll

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("section")
        return label

    def _setting_row(self, key: str, title: str, desc: str, available: bool) -> QWidget:
        row = QFrame()
        row.setObjectName("row")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(12, 9, 12, 9)
        text = QVBoxLayout()
        text.setSpacing(1)
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        title_row.addWidget(QLabel(title))
        if not available:
            soon = QLabel("Próximamente")
            soon.setObjectName("soon")
            title_row.addWidget(soon)
        title_row.addStretch(1)
        text.addLayout(title_row)
        d = QLabel(desc)
        d.setObjectName("desc")
        d.setWordWrap(True)
        text.addWidget(d)
        switch = ToggleSwitch(bool(getattr(self._settings, key)))
        switch.toggled.connect(lambda value, k=key: self._on_switch(k, value))
        self._switches[key] = switch
        lay.addLayout(text, 1)
        lay.addWidget(switch, 0, Qt.AlignVCenter)
        return row

    def _on_switch(self, key: str, value: bool) -> None:
        if key == "voice_enabled":
            self._update_voice_button(value)
        self.setting_changed.emit(key, value)

    def _update_voice_button(self, enabled: bool) -> None:
        self._btn_voice.setText(ICON_VOLUME if enabled else ICON_MUTE)
        self._btn_voice.setToolTip("Silenciar a ROBIN" if enabled else "Activar la voz de ROBIN")

    def set_user_name(self, name: str) -> None:
        self._name_input.setText(name)
        self.reset_view()

    # --- estado de la IA y de la voz -----------------------------------------

    def set_voice_ready(self, ready: bool) -> None:
        self._btn_mic.setEnabled(ready)
        self._btn_mic.setToolTip("Hablarle a ROBIN" if ready else "Preparando el reconocimiento de voz…")

    def set_listening(self, listening: bool) -> None:
        self._listening = listening
        self._btn_mic.setProperty("listening", listening)
        _restyle(self._btn_mic)
        self._btn_mic.setToolTip("Dejar de escuchar" if listening else "Hablarle a ROBIN")
        self._refresh_status()

    def set_transcribing(self, transcribing: bool) -> None:
        self._transcribing = transcribing
        self._refresh_status()

    def set_speaking(self, speaking: bool) -> None:
        self._speaking = speaking
        self._refresh_status()

    def _refresh_status(self) -> None:
        if self._listening:
            text, color = "Escuchando…", "#F87171"
        elif self._confirming:
            text, color = "Esperando tu permiso…", "#F5C451"
        elif self._transcribing:
            text, color = "Entendiendo…", "#F5C451"
        elif self._speaking and self._state is AIState.READY:
            text, color = "Hablando…", "#4FD1FF"
        else:
            text, color = STATUS_TEXT[self._state]
        self._status.setText(text)
        self._dot.setStyleSheet(f"color: {color}; font-size: 9pt;")
        busy = self._state is AIState.BUSY
        can_stop = busy or self._speaking
        self._btn_send.setText(ICON_STOP if can_stop else ICON_SEND)
        self._btn_send.setToolTip("Detener" if can_stop else "Enviar (Enter)")
        self._input.setEnabled(not busy)

    @property
    def ai_ready(self) -> bool:
        return self._state is AIState.READY

    def set_state(self, state: str, message: str) -> None:
        self._state = AIState(state)
        self._refresh_status()
        if self.onboarding_active:
            return
        if self._state in (AIState.READY, AIState.BUSY):
            if self._stack.currentWidget() is self._auth_page:
                self._stack.setCurrentWidget(self._assistant_page)
                self._input.setFocus()
            return
        self._auth_message.setText(message)
        self._btn_login.setVisible(self._state in (AIState.NEEDS_LOGIN, AIState.ERROR))
        self._btn_login.setText("Reintentar" if self._state is AIState.ERROR else "Iniciar sesión con ChatGPT")
        self._btn_cancel_login.setVisible(self._state is AIState.LOGGING_IN)
        self._auth_title.setText(
            "Conectando…" if self._state is AIState.STARTING else "Conecta tu cuenta de ChatGPT"
        )
        if self._stack.currentWidget() is not self._settings_page:
            self._stack.setCurrentWidget(self._auth_page)

    def set_account(self, description: str) -> None:
        self._account_label.setText(description or "Sin sesión")
        self._btn_logout.setVisible(bool(description))

    # --- configuración inicial ---------------------------------------------------

    def begin_onboarding(self) -> None:
        self.onboarding_active = True
        self._stack.setCurrentWidget(self.onboarding)
        self.show_window()

    def end_onboarding(self) -> None:
        self.onboarding_active = False
        self.reset_view()
        self._stack.setCurrentWidget(self._assistant_page)

    # --- vista de asistente (sin historial) --------------------------------------

    def reset_view(self) -> None:
        """Vuelve al saludo: cada vez que se llama a ROBIN empieza de cero."""
        name = self._settings.user_name
        self._greeting.setText(f"Hola, {name}. ¿En qué te ayudo?" if name else "¡Hola! ¿En qué te ayudo?")
        self._greeting.show()
        self._you.clear()
        self._you.hide()
        self._clear_notes()
        self._reply.clear()
        self._reply_text = ""
        self._reply_active = False

    def _clear_notes(self) -> None:
        while self._notes.count() > 1:
            w = self._notes.takeAt(0).widget()
            if w is not None:
                w.deleteLater()

    def _show_request(self, text: str) -> None:
        self._greeting.hide()
        self._clear_notes()
        self._you.setText(f"“{text}”")
        self._you.show()
        self._reply.clear()
        self._reply_text = ""

    def add_note(self, text: str) -> None:
        note = QLabel(f"↗  {text}")
        note.setObjectName("note")
        self._notes.insertWidget(self._notes.count() - 1, note)

    def submit_voice_text(self, text: str) -> None:
        """Texto dictado por voz: se envía como si lo hubieras escrito."""
        if not text:
            self._greeting.setText("No te escuché bien, ¿me repites?")
            return
        if self._state is AIState.READY and not self.onboarding_active:
            self._show_request(text)
            self.send_requested.emit(text)
        else:
            self._input.setText(text)

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text or self._state is not AIState.READY:
            return
        self._input.clear()
        self._show_request(text)
        self.send_requested.emit(text)

    def _on_send_clicked(self) -> None:
        if self._state is AIState.BUSY or (self._speaking and not self._input.text().strip()):
            self.stop_requested.emit()
        else:
            self._on_send()

    def _on_mic_clicked(self) -> None:
        if self._listening:
            self.mic_cancel_requested.emit()
        else:
            self.mic_requested.emit()

    def on_reply_started(self) -> None:
        self._reply_active = True
        self._reply_text = ""
        self._reply.setObjectName("reply")
        _restyle(self._reply)
        self._reply.setText("…")

    def on_reply_delta(self, chunk: str) -> None:
        self._reply_text += chunk
        self._reply.setText(self._reply_text)

    def on_reply_finished(self, text: str) -> None:
        self._reply.setText(text or self._reply_text or "(sin respuesta)")
        self._reply_active = False
        self._input.setFocus()

    def on_reply_failed(self, error: str) -> None:
        self._reply.setObjectName("replyError")
        _restyle(self._reply)
        self._reply.setText(f"Uy, algo falló: {error}")
        self._reply_active = False

    # --- navegación -----------------------------------------------------------

    def _toggle_settings(self) -> None:
        if self._stack.currentWidget() is self._settings_page:
            self._btn_settings.setText(ICON_SETTINGS)
            self._btn_settings.setToolTip("Ajustes")
            if self.onboarding_active:
                self._stack.setCurrentWidget(self.onboarding)
            elif self._state in (AIState.READY, AIState.BUSY):
                self._stack.setCurrentWidget(self._assistant_page)
            else:
                self.set_state(self._state.value, self._auth_message.text())
        else:
            self._btn_settings.setText(ICON_BACK)
            self._btn_settings.setToolTip("Volver")
            self._stack.setCurrentWidget(self._settings_page)

    def show_settings(self) -> None:
        self.show_window()
        if self._stack.currentWidget() is not self._settings_page:
            self._toggle_settings()

    def _on_auth_primary(self) -> None:
        if self._state is AIState.ERROR:
            self.retry_requested.emit()
        else:
            self.login_requested.emit()

    # --- mostrar / ocultar ----------------------------------------------------

    def show_window(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.left() + 16, screen.bottom() - self.HEIGHT - 16)  # abajo a la izquierda
        if not self.isVisible() and not self.onboarding_active and not self._reply_active:
            self.reset_view()
        self.show()
        self.raise_()
        self.activateWindow()
        if self._stack.currentWidget() is self._assistant_page:
            self._input.setFocus()

    def dismiss(self) -> None:
        """Esc / X: deja de escuchar y se va a la bandeja (y rechaza un permiso pendiente)."""
        if self._listening:
            self.mic_cancel_requested.emit()
        if self._confirming:
            self.confirm_answered.emit(False)
        self.hide()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        if self._stack.currentWidget() is self._settings_page:
            self._toggle_settings()
        self.hidden.emit()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._glass_applied:
            self._glass_applied = apply_glass(int(self.winId()))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.dismiss()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        event.ignore()
        self.dismiss()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._header.geometry().contains(event.position().toPoint()):
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()
        super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)
        p.fillPath(path, QColor(16, 18, 26, 120 if self._glass_applied else 235))
        p.setPen(QPen(QColor(255, 255, 255, 38), 1))
        p.drawPath(path)
