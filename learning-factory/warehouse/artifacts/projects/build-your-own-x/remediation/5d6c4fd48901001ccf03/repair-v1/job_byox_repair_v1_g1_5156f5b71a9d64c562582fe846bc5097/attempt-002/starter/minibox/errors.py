"""Minibox's small, stable exception hierarchy."""


class MiniboxError(Exception):
    """Base class for expected Minibox failures."""


class SpecError(MiniboxError):
    """The requested container specification is invalid."""


class RootfsError(MiniboxError):
    """An executable cannot be resolved safely in the root filesystem."""


class StateError(MiniboxError):
    """Persistent lifecycle state is invalid or cannot be transitioned."""


class StateCommitUncertain(StateError):
    """An atomic publication is visible but its durable commit is uncertain.

    ``proposed_state`` is the exact immutable record that the caller attempted
    to publish. Callers must not retry the mutation blindly; pass this error to
    ``StateStore.recover`` on a store for the same directory.
    """

    def __init__(self, proposed_state: object, directory: object, cause: BaseException):
        self.proposed_state = proposed_state
        self._directory = directory
        super().__init__(
            "state publication is visible but durable commit is uncertain; "
            "call StateStore.recover"
        )
        self.__cause__ = cause


class BackendError(MiniboxError):
    """The execution backend failed before returning a process result."""


class BackendUnavailable(BackendError):
    """The host cannot provide the requested execution backend."""


class BackendTimeout(BackendError):
    """The container process exceeded its configured deadline."""
