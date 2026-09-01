"""Stage 2: resolve a command without escaping its proposed rootfs."""

from pathlib import Path

from .config import ContainerSpec


def resolve_executable(spec: ContainerSpec) -> Path:
    """Return the host path of ``spec.argv[0]`` inside ``spec.rootfs``.

    See REQUIREMENTS.md for PATH search, traversal, file-type, permission, and
    symlink rules.
    """

    raise NotImplementedError("stage 2: implement resolve_executable")
