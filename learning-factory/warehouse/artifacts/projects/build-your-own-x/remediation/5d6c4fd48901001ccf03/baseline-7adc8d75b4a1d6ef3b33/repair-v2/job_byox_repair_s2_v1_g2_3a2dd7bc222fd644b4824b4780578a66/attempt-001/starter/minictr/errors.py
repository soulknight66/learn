"""Stable exception types for learner and evaluator code."""


class MiniCtrError(Exception):
    """Base class for expected TinyCtr errors."""


class ValidationError(MiniCtrError, ValueError):
    """A value at a trust boundary is invalid."""


class TransitionError(MiniCtrError, RuntimeError):
    """A durable lifecycle transition is invalid or lost a race."""
