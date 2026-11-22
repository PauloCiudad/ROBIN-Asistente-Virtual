"""Lector mínimo de accesos directos de Windows (.lnk, formato MS-SHLLINK): devuelve la ruta destino local."""

from __future__ import annotations

import struct
from pathlib import Path

_HAS_ID_LIST = 0x01
_HAS_LINK_INFO = 0x02
_VOLUME_AND_LOCAL_BASE = 0x01


def _cstr(data: bytes, start: int, unicode: bool) -> str:
    if unicode:
        end = start
        while end + 1 < len(data) and data[end:end + 2] != b"\x00\x00":
            end += 2
        return data[start:end].decode("utf-16-le", errors="replace")
    end = data.find(b"\x00", start)
    return data[start:end if end >= 0 else len(data)].decode("mbcs", errors="replace")


def lnk_target(path: Path) -> str | None:
    try:
        data = path.read_bytes()
        if len(data) < 0x4C or struct.unpack_from("<I", data, 0)[0] != 0x4C:
            return None
        flags = struct.unpack_from("<I", data, 0x14)[0]
        pos = 0x4C
        if flags & _HAS_ID_LIST:
            pos += 2 + struct.unpack_from("<H", data, pos)[0]
        if not flags & _HAS_LINK_INFO:
            return None
        info = pos
        header_size, info_flags = struct.unpack_from("<II", data, info + 4)
        if not info_flags & _VOLUME_AND_LOCAL_BASE:
            return None  # p. ej. rutas de red
        local_off, _, suffix_off = struct.unpack_from("<III", data, info + 16)
        if header_size >= 0x24:
            local_u, suffix_u = struct.unpack_from("<II", data, info + 28)
            base = _cstr(data, info + local_u, True) if local_u else _cstr(data, info + local_off, False)
            suffix = _cstr(data, info + suffix_u, True) if suffix_u else _cstr(data, info + suffix_off, False)
        else:
            base = _cstr(data, info + local_off, False)
            suffix = _cstr(data, info + suffix_off, False)
        return (base + suffix) or None
    except (OSError, struct.error):
        return None
