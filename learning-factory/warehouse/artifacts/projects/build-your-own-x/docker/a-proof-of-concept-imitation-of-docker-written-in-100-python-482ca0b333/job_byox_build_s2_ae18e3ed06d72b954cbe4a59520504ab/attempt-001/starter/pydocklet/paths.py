"""Path validation primitives (milestone 1)."""

from pathlib import Path, PurePosixPath

from .errors import PathEscape


def safe_member_path(name: str) -> PurePosixPath:
    """Return a safe normalized archive path.

    TODO(1): implement the grammar in REQUIREMENTS.md. Be deliberately strict; tar member names are
    attacker-controlled and platform-specific normalization is surprising.
    """
    raise NotImplementedError("TODO(1): safe_member_path")


def resolve_beneath(root: Path, relative: PurePosixPath) -> Path:
    """Resolve *relative* beneath *root* without following an escaping symlink.

    TODO(1): use structural path comparison and inspect existing parents. A string-prefix check does
    not establish containment.
    """
    raise NotImplementedError("TODO(1): resolve_beneath")
