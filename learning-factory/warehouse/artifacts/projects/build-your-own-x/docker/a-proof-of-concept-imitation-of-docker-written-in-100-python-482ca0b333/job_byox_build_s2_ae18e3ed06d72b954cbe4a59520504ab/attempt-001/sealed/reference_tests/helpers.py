from __future__ import annotations

import io
import tarfile
from pathlib import Path


def tar_with(path: Path, entries: list[tarfile.TarInfo], payloads: list[bytes | None]) -> Path:
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as archive:
        for info, payload in zip(entries, payloads, strict=True):
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, None if payload is None else io.BytesIO(payload))
    return path


def regular(name: str, payload: bytes, mode: int = 0o644) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.type = tarfile.REGTYPE
    info.size = len(payload)
    info.mode = mode
    return info, payload


def directory(name: str, mode: int = 0o700) -> tuple[tarfile.TarInfo, None]:
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.size = 0
    info.mode = mode
    return info, None


def write_regular_layer(path: Path, entries: list[tuple[str, bytes, int]]) -> Path:
    specs = [regular(name, payload, mode) for name, payload, mode in entries]
    return tar_with(path, [spec[0] for spec in specs], [spec[1] for spec in specs])
