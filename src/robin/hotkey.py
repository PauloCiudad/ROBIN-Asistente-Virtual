"""Atajo de teclado global (Alt + X) con RegisterHotKey de Win32.

No usa hooks de teclado ni requiere permisos de administrador: Windows envía WM_HOTKEY a la cola del
hilo principal y un filtro de eventos nativos de Qt lo recoge.
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal

log = logging.getLogger(__name__)

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
_user32.RegisterHotKey.restype = wintypes.BOOL
_user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.UnregisterHotKey.restype = wintypes.BOOL


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey) -> None:
        super().__init__()
        self._on_hotkey = on_hotkey

    def nativeEventFilter(self, event_type, message):
        if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self._on_hotkey(int(msg.wParam))
                return True, 0
        return False, 0


class GlobalHotkey(QObject):
    """Registra un atajo global y emite `activated` cada vez que se pulsa."""

    activated = Signal()
    _next_id = 0xB0B0

    def __init__(self, modifiers: int, vk: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        GlobalHotkey._next_id += 1
        self._id = GlobalHotkey._next_id
        self._filter = _Filter(self._dispatch)
        QCoreApplication.instance().installNativeEventFilter(self._filter)
        self.registered = bool(_user32.RegisterHotKey(None, self._id, modifiers | MOD_NOREPEAT, vk))
        if not self.registered:
            log.warning("No se pudo registrar el atajo global (error %s)", ctypes.get_last_error())

    def _dispatch(self, hotkey_id: int) -> None:
        if hotkey_id == self._id:
            self.activated.emit()

    def unregister(self) -> None:
        if self.registered:
            _user32.UnregisterHotKey(None, self._id)
            self.registered = False
        QCoreApplication.instance().removeNativeEventFilter(self._filter)
