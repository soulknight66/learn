"""Optional compiler for Pebble's pure expression subset."""

from dataclasses import dataclass
from typing import Any

from .errors import ArityError, CompileError
from .values import Symbol


@dataclass(frozen=True, slots=True)
class Instruction:
    operation: str
    argument: Any = None


@dataclass(frozen=True, slots=True)
class Program:
    instructions: tuple[Instruction, ...]
    constants: tuple[Any, ...]


class Compiler:
    """Compile literals, loads, quote, if, do, and ordinary calls."""

    def __init__(self) -> None:
        self._instructions: list[Instruction] = []
        self._constants: list[Any] = []

    def compile(self, form: Any) -> Program:
        self._instructions = []
        self._constants = []
        self._compile_form(form)
        self._emit("RETURN")
        return Program(tuple(self._instructions), tuple(self._constants))

    def _emit(self, operation: str, argument: Any = None) -> int:
        self._instructions.append(Instruction(operation, argument))
        return len(self._instructions) - 1

    def _patch(self, index: int, target: int) -> None:
        instruction = self._instructions[index]
        self._instructions[index] = Instruction(instruction.operation, target)

    def _constant(self, value: Any) -> None:
        self._constants.append(value)
        self._emit("CONST", len(self._constants) - 1)

    def _compile_form(self, form: Any) -> None:
        if isinstance(form, Symbol):
            self._emit("LOAD", form.name)
            return
        if not isinstance(form, list):
            self._constant(form)
            return
        if not form:
            self._constant([])
            return

        operator = form[0]
        arguments = form[1:]
        if isinstance(operator, Symbol) and operator.name == "quote":
            if len(arguments) != 1:
                raise ArityError(
                    f"quote: expected 1 argument(s), received {len(arguments)}"
                )
            self._constant(arguments[0])
            return
        if isinstance(operator, Symbol) and operator.name == "if":
            if len(arguments) not in (2, 3):
                raise ArityError(
                    f"if: expected 2 to 3 argument(s), received {len(arguments)}"
                )
            self._compile_form(arguments[0])
            false_jump = self._emit("JUMP_IF_FALSE")
            self._compile_form(arguments[1])
            end_jump = self._emit("JUMP")
            self._patch(false_jump, len(self._instructions))
            self._compile_form(arguments[2] if len(arguments) == 3 else None)
            self._patch(end_jump, len(self._instructions))
            return
        if isinstance(operator, Symbol) and operator.name == "do":
            if not arguments:
                self._constant(None)
                return
            for expression in arguments[:-1]:
                self._compile_form(expression)
                self._emit("POP")
            self._compile_form(arguments[-1])
            return
        if isinstance(operator, Symbol) and operator.name in {"def", "let", "fn"}:
            raise CompileError(f"unsupported special form '{operator.name}'")

        self._compile_form(operator)
        for argument in arguments:
            self._compile_form(argument)
        self._emit("CALL", len(arguments))
