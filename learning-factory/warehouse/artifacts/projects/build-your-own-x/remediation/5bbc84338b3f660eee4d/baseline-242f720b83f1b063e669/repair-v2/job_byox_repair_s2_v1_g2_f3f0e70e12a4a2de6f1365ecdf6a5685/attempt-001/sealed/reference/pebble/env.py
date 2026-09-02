"""Lexical environment frames."""

from typing import Any, Mapping

from .errors import NameResolutionError


class Environment:
    def __init__(
        self,
        parent: "Environment | None" = None,
        initial: Mapping[str, Any] | None = None,
    ) -> None:
        self.parent = parent
        self.bindings: dict[str, Any] = dict(initial or {})

    def define(self, name: str, value: Any) -> Any:
        self.bindings[name] = value
        return value

    def lookup(self, name: str) -> Any:
        environment: Environment | None = self
        while environment is not None:
            if name in environment.bindings:
                return environment.bindings[name]
            environment = environment.parent
        raise NameResolutionError(f"unbound symbol '{name}'")
