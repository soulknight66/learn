from __future__ import annotations

from dataclasses import dataclass

from .model import Assign, Binary, Block, CompileError, Expr, If, Let, Literal, Print, Program, Unary, Variable, While


@dataclass(frozen=True)
class Instruction:
    opcode: str
    operand: int | str | None = None


@dataclass(frozen=True)
class BytecodeProgram:
    instructions: tuple[Instruction, ...]


class Compiler:
    def __init__(self) -> None:
        self.code: list[Instruction] = []

    def compile(self, program: Program) -> BytecodeProgram:
        for statement in program.statements:
            self._statement(statement)
        self._emit("HALT")
        return BytecodeProgram(tuple(self.code))

    def _emit(self, opcode: str, operand: int | str | None = None) -> int:
        self.code.append(Instruction(opcode, operand))
        return len(self.code) - 1

    def _patch(self, location: int, target: int) -> None:
        instruction = self.code[location]
        if instruction.opcode not in {"JUMP", "JUMP_IF_FALSE", "JUMP_IF_TRUE"}:
            raise CompileError("attempted to patch a non-jump instruction")
        self.code[location] = Instruction(instruction.opcode, target)

    def _statement(self, statement) -> None:
        self._emit("TICK")
        if isinstance(statement, Let):
            self._expression(statement.initializer)
            self._emit("DEFINE", statement.name)
            return
        if isinstance(statement, Assign):
            self._expression(statement.value)
            self._emit("STORE", statement.name)
            return
        if isinstance(statement, Print):
            self._expression(statement.expression)
            self._emit("PRINT")
            return
        if isinstance(statement, Block):
            for child in statement.statements:
                self._statement(child)
            return
        if isinstance(statement, If):
            self._expression(statement.condition)
            false_jump = self._emit("JUMP_IF_FALSE", -1)
            self._statement(statement.then_branch)
            end_jump = self._emit("JUMP", -1)
            self._patch(false_jump, len(self.code))
            if statement.else_branch is not None:
                self._statement(statement.else_branch)
            self._patch(end_jump, len(self.code))
            return
        if isinstance(statement, While):
            loop_start = len(self.code)
            self._expression(statement.condition)
            exit_jump = self._emit("JUMP_IF_FALSE", -1)
            self._statement(statement.body)
            self._emit("JUMP", loop_start)
            self._patch(exit_jump, len(self.code))
            return
        raise CompileError(f"unsupported statement: {type(statement).__name__}")

    def _expression(self, expression: Expr) -> None:
        self._emit("TICK")
        if isinstance(expression, Literal):
            self._emit("CONST", expression.value)
            return
        if isinstance(expression, Variable):
            self._emit("LOAD", expression.name)
            return
        if isinstance(expression, Unary):
            if expression.operator == "-" and isinstance(expression.right, Literal) and expression.right.value == 2 ** 63:
                self._emit("TICK")
                self._emit("CONST", -(2 ** 63))
                return
            self._expression(expression.right)
            self._emit({"-": "NEG", "!": "NOT"}[expression.operator])
            return
        if isinstance(expression, Binary) and expression.operator == "&&":
            self._expression(expression.left)
            false_jump = self._emit("JUMP_IF_FALSE", -1)
            self._expression(expression.right)
            self._emit("BOOL")
            end_jump = self._emit("JUMP", -1)
            self._patch(false_jump, len(self.code))
            self._emit("CONST", 0)
            self._patch(end_jump, len(self.code))
            return
        if isinstance(expression, Binary) and expression.operator == "||":
            self._expression(expression.left)
            true_jump = self._emit("JUMP_IF_TRUE", -1)
            self._expression(expression.right)
            self._emit("BOOL")
            end_jump = self._emit("JUMP", -1)
            self._patch(true_jump, len(self.code))
            self._emit("CONST", 1)
            self._patch(end_jump, len(self.code))
            return
        if isinstance(expression, Binary):
            self._expression(expression.left)
            self._expression(expression.right)
            opcode = {
                "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
                "==": "EQ", "!=": "NE", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE",
            }.get(expression.operator)
            if opcode is None:
                raise CompileError(f"unsupported operator: {expression.operator}")
            self._emit(opcode)
            return
        raise CompileError(f"unsupported expression: {type(expression).__name__}")


def compile_program(program: Program) -> BytecodeProgram:
    return Compiler().compile(program)
