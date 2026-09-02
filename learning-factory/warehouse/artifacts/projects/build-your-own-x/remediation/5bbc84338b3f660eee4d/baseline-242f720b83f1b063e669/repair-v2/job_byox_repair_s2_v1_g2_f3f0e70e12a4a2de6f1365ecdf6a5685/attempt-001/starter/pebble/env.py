"""Lexical environment scaffold."""

from typing import Any, Mapping


class Environment:
    def __init__(
        self,
        parent: "Environment | None" = None,
        initial: Mapping[str, Any] | None = None,
    ) -> None:
        self.parent = parent
        self.bindings: dict[str, Any] = dict(initial or {})

    def define(self, name: str, value: Any) -> Any:
        raise NotImplementedError("TODO: bind a name in this frame")

    def lookup(self, name: str) -> Any:
        raise NotImplementedError("TODO: resolve through lexical parents")
