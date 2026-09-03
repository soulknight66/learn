"""Intentionally flawed code for the debugging exercise."""

from pathlib import Path


def resolve_beneath(root: Path, guest: str) -> Path:
    candidate = (root / guest.lstrip("/")).resolve()
    if not str(candidate).startswith(str(root.resolve())):
        raise ValueError("outside root")
    return candidate
