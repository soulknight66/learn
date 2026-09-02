"""Tree-walking interpreter scaffold."""

from collections.abc import Callable
from typing import Any

from .env import Environment


class Interpreter:
    """A stateful Pebble interpreter with one persistent global frame."""

    def __init__(self, output: Callable[[str], None] | None = None) -> None:
        self.output = output if output is not None else print
        self.globals = Environment()
        self._install_builtins()

    def _install_builtins(self) -> None:
        """Populate ``self.globals`` with the required built-ins."""

        # Leave construction usable so reader work can be tested independently.

    def eval(self, form: Any, env: Environment | None = None) -> Any:
        """Evaluate one already-read form."""

        raise NotImplementedError("TODO: implement evaluation")

    def eval_source(self, source: str) -> Any:
        """Read and evaluate all forms, preserving globals between calls."""

        raise NotImplementedError("TODO: connect reader and evaluator")
