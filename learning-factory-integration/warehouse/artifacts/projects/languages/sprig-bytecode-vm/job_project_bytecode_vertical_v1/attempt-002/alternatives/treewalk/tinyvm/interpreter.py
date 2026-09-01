from __future__ import annotations

from .model import Assign, Binary, Block, ExecutionResult, If, Let, Literal, Print, Program, ResourceLimit, RuntimeFault, Unary, Variable, While
from .semantics import binary, checked, truth


class Interpreter:
    def __init__(self, max_steps: int):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps = max_steps
        self.steps = 0
        self.environment: dict[str, int] = {}
        self.outputs: list[int] = []

    def tick(self) -> None:
        if self.steps >= self.max_steps:
            raise ResourceLimit(f"evaluation budget exceeded ({self.max_steps})")
        self.steps += 1

    def run(self, program: Program) -> ExecutionResult:
        for statement in program.statements:
            self.statement(statement)
        return ExecutionResult(tuple(self.outputs), dict(self.environment), self.steps, "treewalk")

    def statement(self, statement) -> None:
        self.tick()
        if isinstance(statement, Let):
            value = self.expression(statement.initializer)
            if statement.name in self.environment:
                raise RuntimeFault(f"duplicate variable: {statement.name}")
            self.environment[statement.name] = value
        elif isinstance(statement, Assign):
            value = self.expression(statement.value)
            if statement.name not in self.environment:
                raise RuntimeFault(f"undefined variable: {statement.name}")
            self.environment[statement.name] = value
        elif isinstance(statement, Print):
            self.outputs.append(self.expression(statement.expression))
        elif isinstance(statement, Block):
            for child in statement.statements: self.statement(child)
        elif isinstance(statement, If):
            branch = statement.then_branch if self.expression(statement.condition) else statement.else_branch
            if branch is not None: self.statement(branch)
        elif isinstance(statement, While):
            while self.expression(statement.condition): self.statement(statement.body)
        else:
            raise RuntimeFault(f"unsupported statement: {type(statement).__name__}")

    def expression(self, expression) -> int:
        self.tick()
        if isinstance(expression, Literal): return checked(expression.value)
        if isinstance(expression, Variable):
            if expression.name not in self.environment:
                raise RuntimeFault(f"undefined variable: {expression.name}")
            return self.environment[expression.name]
        if isinstance(expression, Unary):
            if expression.operator == "-" and isinstance(expression.right, Literal) and expression.right.value == 2 ** 63:
                self.tick()
                return -(2 ** 63)
            value = self.expression(expression.right)
            if expression.operator == "-": return checked(-value)
            if expression.operator == "!": return int(value == 0)
        if isinstance(expression, Binary):
            left = self.expression(expression.left)
            if expression.operator == "&&": return truth(self.expression(expression.right)) if left else 0
            if expression.operator == "||": return 1 if left else truth(self.expression(expression.right))
            return binary(expression.operator, left, self.expression(expression.right))
        raise RuntimeFault(f"unsupported expression: {type(expression).__name__}")


def execute(program: Program, *, max_steps: int = 10_000) -> ExecutionResult:
    return Interpreter(max_steps).run(program)
