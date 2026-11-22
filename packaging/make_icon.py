"""Genera packaging/robin.ico (varios tamaños, PNG embebido) a partir del icono que dibuja ROBIN."""

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication

from robin.ui.widgets import robin_icon

SIZES = [16, 24, 32, 48, 64, 128, 256]


def main(out: Path) -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841 — necesario para dibujar
    icon = robin_icon(256)
    images = []
    for size in SIZES:
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        icon.pixmap(size, size).save(buffer, "PNG")
        images.append((size, bytes(data)))
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, png in images:
        dim = 0 if size >= 256 else size  # 0 significa 256 en el formato ICO
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(blobs))
        blobs += png
    out.write_bytes(header + entries + blobs)
    print(f"Icono creado: {out} ({len(images)} tamaños)")


if __name__ == "__main__":
    main(Path(__file__).with_name("robin.ico"))
