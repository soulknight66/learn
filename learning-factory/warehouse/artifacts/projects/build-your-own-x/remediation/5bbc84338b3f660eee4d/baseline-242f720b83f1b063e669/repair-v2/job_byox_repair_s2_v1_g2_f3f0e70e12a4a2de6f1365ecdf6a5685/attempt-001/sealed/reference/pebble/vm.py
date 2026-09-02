"""Stack virtual machine for programs produced by ``pebble.compiler``."""

from typing import Any

from .compiler import Program
from .errors import EvalError
from .interpreter import Interpreter, is_falsey
from .values import Builtin, format_value


class VirtualMachine:
    def __init__(self, interpreter: Interpreter | None = None) -> None:
        self.interpreter = interpreter if interpreter is not None else Interpreter()

    @staticmethod
    def _pop(stack: list[Any], operation: str) -> Any:
        if not stack:
            raise EvalError(f"vm: stack underflow during {operation}")
        return stack.pop()

    @staticmethod
    def _target(value: Any, length: int) -> int:
        if type(value) is not int or value < 0 or value >= length:
            raise EvalError(f"vm: invalid jump target {value!r}")
        return value

    def run(self, program: Program) -> Any:
        instructions = program.instructions
        constants = program.constants
        stack: list[Any] = []
        pointer = 0

        while pointer < len(instructions):
            instruction = instructions[pointer]
            pointer += 1
            operation = instruction.operation
            argument = instruction.argument

            if operation == "CONST":
                if type(argument) is not int or not 0 <= argument < len(constants):
                    raise EvalError(f"vm: invalid constant index {argument!r}")
                stack.append(constants[argument])
            elif operation == "LOAD":
                if not isinstance(argument, str):
                    raise EvalError("vm: LOAD requires a string name")
                stack.append(self.interpreter.globals.lookup(argument))
            elif operation == "POP":
                self._pop(stack, operation)
            elif operation == "JUMP_IF_FALSE":
                target = self._target(argument, len(instructions))
                condition = self._pop(stack, operation)
                if is_falsey(condition):
                    pointer = target
            elif operation == "JUMP":
                pointer = self._target(argument, len(instructions))
            elif operation == "CALL":
                if type(argument) is not int or argument < 0:
                    raise EvalError(f"vm: invalid call arity {argument!r}")
                if len(stack) < argument + 1:
                    raise EvalError("vm: stack underflow during CALL")
                if argument:
                    values = stack[-argument:]
                    del stack[-argument:]
                else:
                    values = []
                callee = stack.pop()
                if not isinstance(callee, Builtin):
                    raise EvalError(
                        f"vm: calls are limited to built-ins, received {format_value(callee)}"
                    )
                stack.append(callee.invoke(values))
            elif operation == "RETURN":
                value = self._pop(stack, operation)
                if stack:
                    raise EvalError("vm: RETURN found extra stack values")
                return value
            else:
                raise EvalError(f"vm: unknown instruction {operation!r}")

        raise EvalError("vm: program ended without RETURN")
