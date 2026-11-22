"""Observadores de actividad (respetan sus switches en caliente):
- AppObserver: qué programa está en primer plano (solo el ejecutable; nunca títulos de ventana).
- FileObserver: archivos abiertos recientemente según la carpeta "Recientes" de Windows.
"""

from __future__ import annotations

import ctypes
import logging
import os
import time
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from robin.learning.activity import ActivityLog
from robin.learning.files_filter import is_trackable_file
from robin.learning.lnk import lnk_target

log = logging.getLogger(__name__)

_user32 = ctypes.WinDLL("user32")
_kernel32 = ctypes.WinDLL("kernel32")
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Procesos del sistema o de fondo que no son "apps que el usuario abre".
IGNORED_EXES = {
    "explorer.exe", "applicationframehost.exe", "shellexperiencehost.exe", "searchhost.exe",
    "startmenuexperiencehost.exe", "lockapp.exe", "textinputhost.exe", "python.exe", "pythonw.exe",
    "taskmgr.exe", "systemsettings.exe", "searchapp.exe", "shellhost.exe", "widgets.exe", "dwm.exe",
    "rundll32.exe", "consent.exe", "openwith.exe", "pickerhost.exe",
}
APP_REOPEN_GAP_S = 30 * 60  # volver a una app tras 30 min sin usarla cuenta como "abrirla" de nuevo


def foreground_exe() -> str | None:
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return None
    finally:
        _kernel32.CloseHandle(handle)


class AppObserver(QObject):
    def __init__(self, log_: ActivityLog, enabled: Callable[[], bool], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._log = log_
        self._enabled = enabled
        self._current: str | None = None
        self._last_seen: dict[str, float] = {}
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(5000)

    def _poll(self) -> None:
        if not self._enabled():
            self._current = None
            return
        path = foreground_exe()
        if not path:
            return
        exe = os.path.basename(path)
        if exe.casefold() in IGNORED_EXES:
            return
        now = time.time()
        if exe != self._current and now - self._last_seen.get(exe, 0) > APP_REOPEN_GAP_S:
            self._log.record("app", "app_open", exe, {"path": path})
        self._current = exe
        self._last_seen[exe] = now


class FileObserver(QObject):
    def __init__(self, log_: ActivityLog, enabled: Callable[[], bool], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._log = log_
        self._enabled = enabled
        self._recent = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Recent"
        self._last_check = time.time()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(60_000)

    def _poll(self) -> None:
        since, self._last_check = self._last_check, time.time()
        if not self._enabled() or not self._recent.is_dir():
            return
        try:
            entries = [e for e in os.scandir(self._recent) if e.name.lower().endswith(".lnk")]
        except OSError:
            return
        for entry in entries:
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime < since:
                continue
            target = lnk_target(Path(entry.path))
            if target and is_trackable_file(target):
                self._log.record("file", "file_open", os.path.basename(target), {"path": target}, ts=mtime)
