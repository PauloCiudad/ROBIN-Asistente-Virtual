"""Efecto glass (desenfoque Acrylic de Windows) y esquinas redondeadas vía DWM, con ctypes.

Si alguna llamada falla (versión de Windows distinta), la ventana sigue funcionando con su fondo
semitransparente pintado por Qt.
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

log = logging.getLogger(__name__)

_WCA_ACCENT_POLICY = 19
_ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_ROUND = 2


class _AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class _WinCompAttrData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(_AccentPolicy)),
        ("SizeOfData", ctypes.c_size_t),
    ]


def _dwm_set_int(hwnd: int, attribute: int, value: int) -> None:
    val = ctypes.c_int(value)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd), attribute, ctypes.byref(val), ctypes.sizeof(val)
    )


def apply_glass(hwnd: int, tint: tuple[int, int, int, int] = (18, 20, 28, 120)) -> bool:
    """Activa el desenfoque Acrylic detrás de la ventana. `tint` es (r, g, b, alpha)."""
    r, g, b, a = tint
    try:
        _dwm_set_int(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 1)
        _dwm_set_int(hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE, _DWMWCP_ROUND)
        accent = _AccentPolicy(_ACCENT_ENABLE_ACRYLICBLURBEHIND, 2, (a << 24) | (b << 16) | (g << 8) | r, 0)
        data = _WinCompAttrData(_WCA_ACCENT_POLICY, ctypes.pointer(accent), ctypes.sizeof(accent))
        ok = bool(ctypes.windll.user32.SetWindowCompositionAttribute(wintypes.HWND(hwnd), ctypes.byref(data)))
        if not ok:
            log.warning("SetWindowCompositionAttribute devolvió 0; se usa fondo sin desenfoque")
        return ok
    except (AttributeError, OSError):
        log.exception("No se pudo aplicar el efecto glass")
        return False
