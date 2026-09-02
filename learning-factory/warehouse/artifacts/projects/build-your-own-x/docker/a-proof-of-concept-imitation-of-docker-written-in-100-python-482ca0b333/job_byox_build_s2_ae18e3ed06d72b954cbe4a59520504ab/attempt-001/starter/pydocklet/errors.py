"""Domain errors exposed by PyDocklet."""


class PyDockletError(Exception):
    """Base class for expected, user-facing failures."""


class PathEscape(PyDockletError):
    """A path could escape its assigned root."""


class InvalidLayer(PyDockletError):
    """An image layer is malformed, unsupported, or over quota."""


class InvalidName(PyDockletError):
    """A user-provided identifier is outside the public grammar."""


class Conflict(PyDockletError):
    """An existing object conflicts with a requested operation."""


class NotFound(PyDockletError):
    """A requested image or container does not exist."""


class InvalidTransition(PyDockletError):
    """A lifecycle transition is not allowed."""


class InvalidProcess(PyDockletError):
    """A process request is structurally invalid."""
