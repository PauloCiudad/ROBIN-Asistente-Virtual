"""Widgets reutilizables: switch animado e icono de ROBIN."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QAbstractButton, QWidget

ACCENT = QColor("#8B7CFF")
ACCENT_2 = QColor("#4FD1FF")


class ToggleSwitch(QAbstractButton):
    """Switch tipo iOS/Windows 11 con animación."""

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:
        return QSize(40, 22)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = rect.height() / 2
        off = QColor(255, 255, 255, 40)
        track = QColor(
            int(off.red() + (ACCENT.red() - off.red()) * self._offset),
            int(off.green() + (ACCENT.green() - off.green()) * self._offset),
            int(off.blue() + (ACCENT.blue() - off.blue()) * self._offset),
            int(off.alpha() + (255 - off.alpha()) * self._offset),
        )
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(rect, radius, radius)
        knob_d = rect.height() - 6
        x = rect.left() + 3 + (rect.width() - knob_d - 6) * self._offset
        p.setBrush(QColor("white") if self.isEnabled() else QColor(255, 255, 255, 120))
        p.drawEllipse(QRectF(x, rect.top() + 3, knob_d, knob_d))


def robin_icon(size: int = 64) -> QIcon:
    """Icono generado por código: círculo con degradado y una 'R'."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, ACCENT)
    grad.setColorAt(1, ACCENT_2)
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawEllipse(1, 1, size - 2, size - 2)
    font = QFont("Segoe UI", int(size * 0.42))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("white"))
    p.drawText(pix.rect(), Qt.AlignCenter, "R")
    p.end()
    return QIcon(pix)
