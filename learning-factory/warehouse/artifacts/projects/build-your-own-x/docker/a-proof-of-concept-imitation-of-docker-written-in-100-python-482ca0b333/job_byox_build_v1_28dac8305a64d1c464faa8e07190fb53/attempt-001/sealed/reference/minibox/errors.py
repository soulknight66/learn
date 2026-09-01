"""Domain errors kept separate from implementation-specific exceptions."""


class MiniBoxError(Exception):
    """Base class for expected MiniBox failures."""


class InvalidIdentifier(MiniBoxError, ValueError):
    pass


class InvalidSpec(MiniBoxError, ValueError):
    pass


class InvalidTransition(MiniBoxError, ValueError):
    pass


class InvalidArchive(MiniBoxError, ValueError):
    pass


class ContainerExists(MiniBoxError):
    pass


class ContainerNotFound(MiniBoxError):
    pass


class StateConflict(MiniBoxError):
    pass


class StateCorruption(MiniBoxError):
    pass


class ImageExists(MiniBoxError):
    pass


class ImageNotFound(MiniBoxError):
    pass


class BackendUnavailable(MiniBoxError):
    pass


class RunError(MiniBoxError):
    pass
