"""Intentionally faulty fragment for the adjacent debugging prompt."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Function:
    parameters: tuple[str, ...]
    body: Any
    definition_environment: Any


def prepare_call(function: Function, values: list[Any], caller_environment: Any):
    # The parent choice is intentionally wrong: lookup now depends on the caller.
    return {
        "parent": caller_environment,
        "bindings": dict(zip(function.parameters, values)),
    }
