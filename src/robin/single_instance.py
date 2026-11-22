"""Garantiza una sola instancia de ROBIN; una segunda ejecución pide a la primera que se muestre."""

from __future__ import annotations

import getpass

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

_SERVER_NAME = f"ROBIN-single-instance-{getpass.getuser()}"


def notify_running_instance() -> bool:
    """Devuelve True si ya había una instancia (y le envió 'show')."""
    socket = QLocalSocket()
    socket.connectToServer(_SERVER_NAME)
    if not socket.waitForConnected(300):
        return False
    socket.write(b"show")
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


class InstanceServer(QObject):
    show_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server = QLocalServer(self)
        QLocalServer.removeServer(_SERVER_NAME)  # limpia restos de un cierre abrupto
        self._server.listen(_SERVER_NAME)
        self._server.newConnection.connect(self._on_connection)

    def _on_connection(self) -> None:
        conn = self._server.nextPendingConnection()
        if conn is not None:
            conn.readyRead.connect(lambda: self._on_message(conn))

    def _on_message(self, conn: QLocalSocket) -> None:
        if bytes(conn.readAll()).strip() == b"show":
            self.show_requested.emit()
        conn.disconnectFromServer()
