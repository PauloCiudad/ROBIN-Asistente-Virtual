"""Página de configuración inicial: nombre del usuario y entrenamiento de voz."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget

from robin.ui.widgets import robin_icon

STATUS_COLORS = {"info": "rgba(242,243,247,0.75)", "ok": "#4ADE80", "warn": "#F5C451", "listen": "#F87171"}


class OnboardingPage(QWidget):
    primary_clicked = Signal()
    secondary_clicked = Signal()
    skip_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 4, 16, 8)
        lay.setSpacing(10)

        self._step = QLabel()
        self._step.setObjectName("hint")
        self._step.setAlignment(Qt.AlignCenter)
        logo = QLabel()
        logo.setPixmap(robin_icon(128).pixmap(56, 56))
        logo.setAlignment(Qt.AlignCenter)
        self._title = QLabel()
        self._title.setObjectName("desc")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setWordWrap(True)
        self._prompt = QLabel()
        self._prompt.setObjectName("bigtitle")
        self._prompt.setAlignment(Qt.AlignCenter)
        self._prompt.setWordWrap(True)

        self._name = QLineEdit()
        self._name.setPlaceholderText("Tu nombre")
        self._name.setAlignment(Qt.AlignCenter)
        self._name.returnPressed.connect(self.primary_clicked)

        self._level = QProgressBar()
        self._level.setObjectName("level")
        self._level.setRange(0, 100)
        self._level.setTextVisible(False)
        self._level.setFixedHeight(6)

        self._status = QLabel()
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setWordWrap(True)

        self._btn_primary = QPushButton()
        self._btn_primary.setObjectName("primary")
        self._btn_primary.setCursor(Qt.PointingHandCursor)
        self._btn_primary.clicked.connect(self.primary_clicked)
        self._btn_secondary = QPushButton()
        self._btn_secondary.setObjectName("secondary")
        self._btn_secondary.setCursor(Qt.PointingHandCursor)
        self._btn_secondary.clicked.connect(self.secondary_clicked)
        self._btn_skip = QPushButton("Omitir el entrenamiento de voz")
        self._btn_skip.setObjectName("link")
        self._btn_skip.setCursor(Qt.PointingHandCursor)
        self._btn_skip.clicked.connect(self.skip_clicked)

        lay.addWidget(self._step)
        lay.addStretch(1)
        for w in (logo, self._title, self._prompt, self._name, self._level, self._status):
            lay.addWidget(w)
        lay.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addWidget(self._btn_secondary)
        buttons.addWidget(self._btn_primary, 1)
        lay.addLayout(buttons)
        lay.addWidget(self._btn_skip, 0, Qt.AlignCenter)

    def show_step(self, step: str, title: str, prompt: str, *, name_field: bool = False,
                  primary: str = "", secondary: str = "", can_skip: bool = True) -> None:
        self._step.setText(step)
        self._title.setText(title)
        self._prompt.setText(prompt)
        self._name.setVisible(name_field)
        self._level.setVisible(not name_field)
        self._btn_primary.setText(primary)
        self._btn_primary.setVisible(bool(primary))
        self._btn_secondary.setText(secondary)
        self._btn_secondary.setVisible(bool(secondary))
        self._btn_skip.setVisible(can_skip)
        self.set_status("", "info")
        self.set_level(0)
        if name_field:
            self._name.setFocus()

    def set_status(self, text: str, kind: str = "info") -> None:
        self._status.setText(text)
        self._status.setStyleSheet(f"color: {STATUS_COLORS.get(kind, STATUS_COLORS['info'])};")

    def set_level(self, value: float) -> None:
        self._level.setValue(int(max(0.0, min(1.0, value)) * 100))

    def name(self) -> str:
        return self._name.text().strip()

    def set_name(self, name: str) -> None:
        self._name.setText(name)
        self._name.selectAll()
        self._name.setFocus()
