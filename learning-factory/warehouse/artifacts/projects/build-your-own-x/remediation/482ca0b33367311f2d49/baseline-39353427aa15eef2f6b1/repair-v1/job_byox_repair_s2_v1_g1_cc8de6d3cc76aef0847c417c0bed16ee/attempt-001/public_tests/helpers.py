"""Small deterministic tar builder used by public tests."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path
from typing import Iterable


def write_layer(path: Path, entries: Iterable[tuple[str, bytes | None, int]]) -> Path:
    """Write entries `(name, contents-or-None-for-directory, mode)` as a plain tar."""
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as archive:
        for name, contents, mode in entries:
            info = tarfile.TarInfo(name)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = mode
            if contents is None:
                info.type = tarfile.DIRTYPE
                info.size = 0
                archive.addfile(info)
            else:
                info.type = tarfile.REGTYPE
                info.size = len(contents)
                archive.addfile(info, io.BytesIO(contents))
    return path


def write_symlink_layer(path: Path, name: str, target: str) -> Path:
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as archive:
        info = tarfile.TarInfo(name)
        info.type = tarfile.SYMTYPE
        info.linkname = target
        info.mode = 0o777
        info.mtime = 0
        archive.addfile(info)
    return path
