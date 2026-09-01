"""Minibox's small, stable exception hierarchy."""


class MiniboxError(Exception):
    """Base class for expected Minibox failures."""


class SpecError(MiniboxError):
    """The requested container specification is invalid."""


class RootfsError(MiniboxError):
    """An executable cannot be resolved safely in the root filesystem."""


class StateError(MiniboxError):
    """Persistent lifecycle state is invalid or cannot be transitioned."""


class BackendError(MiniboxError):
    """The execution backend failed before returning a process result."""


class BackendUnavailable(BackendError):
    """The host cannot provide the requested execution backend."""


class BackendTimeout(BackendError):
    """The container process exceeded its configured deadline."""
