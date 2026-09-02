"""Instructor answer for the path-escape debugging exercise."""

from pathlib import Path, PurePosixPath


def resolve_beneath(root: Path, guest: str) -> Path:
    root = root.resolve(strict=True)
    path = PurePosixPath(guest)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("invalid guest path")
    candidate = root.joinpath(*path.parts[1:]).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("outside root") from exc
    return candidate
