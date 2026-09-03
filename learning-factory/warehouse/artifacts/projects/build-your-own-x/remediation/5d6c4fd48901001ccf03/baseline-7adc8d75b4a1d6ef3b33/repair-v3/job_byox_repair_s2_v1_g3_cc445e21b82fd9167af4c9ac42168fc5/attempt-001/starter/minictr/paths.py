"""Host-side filesystem validation for a learner-created rootfs."""

from pathlib import Path, PurePosixPath

from .errors import ValidationError


def validate_rootfs(path: Path) -> Path:
    if not isinstance(path, Path):
        raise ValidationError("rootfs must be a Path")
    if not path.is_absolute():
        raise ValidationError("rootfs must be absolute")
    if path.is_symlink():
        raise ValidationError("rootfs may not itself be a symlink")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValidationError("rootfs does not resolve") from exc
    if not resolved.is_dir():
        raise ValidationError("rootfs must be a directory")
    if resolved == Path(resolved.anchor):
        raise ValidationError("host filesystem root may not be used as rootfs")
    return resolved


def resolve_guest_path(rootfs: Path, guest_path: str) -> Path:
    root = validate_rootfs(rootfs)
    if not isinstance(guest_path, str) or "\0" in guest_path:
        raise ValidationError("guest path must be a string without NUL")
    guest = PurePosixPath(guest_path)
    if not guest.is_absolute():
        raise ValidationError("guest path must be absolute")
    if ".." in guest.parts:
        raise ValidationError("guest path may not contain parent traversal")
    try:
        candidate = root.joinpath(*guest.parts[1:]).resolve(strict=False)
        candidate.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValidationError("guest path escapes rootfs") from exc
    return candidate
