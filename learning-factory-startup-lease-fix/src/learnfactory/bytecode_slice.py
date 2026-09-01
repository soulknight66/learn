from __future__ import annotations

import json
import sqlite3
from difflib import unified_diff
from pathlib import Path
from textwrap import dedent
from typing import Any

from .db import Database
from .util import redact, tree_sha256
from .vertical_slices import SliceResult


PROJECT_ID = "project_4b7f4b85b17b06eeba75d235767a898f"
_DEFAULT_PROVENANCE = {
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "source_name": "Build Your Own X",
    "source_path": "../build-your-own-x",
    "upstream_url": "https://github.com/codecrafters-io/build-your-own-x",
    "commit_hash": "aa17439b62f384511a5561ce308e9598b94d8989",
    "license": "CC0-1.0",
    "project_id": PROJECT_ID,
    "project_slug": "home-grown-bytecode-interpreters",
    "project_title": "Home-grown bytecode interpreters",
    "project_category": "Emulator / Virtual Machine",
    "implementation_language": "C",
    "external_reference": (
        "https://medium.com/bumble-tech/home-grown-bytecode-interpreters-51e12d59b25c"
    ),
    "linked_resource_license": "NOASSERTION",
    "source_reference": "README.md:166",
}


def _clean(value: object, *, limit: int = 2_000) -> str:
    return redact(str(value), limit=limit).strip()


def _target(workspace: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe generated path: {relative!r}")
    root = workspace.resolve()
    destination = workspace / path
    try:
        destination.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(f"generated path escapes workspace: {relative!r}") from error
    parent = workspace
    for part in path.parts[:-1]:
        parent /= part
        if parent.is_symlink():
            raise ValueError(f"generated path traverses symlink: {relative!r}")
        parent.mkdir(exist_ok=True)
    if destination.is_symlink():
        raise ValueError(f"refusing to overwrite symlink: {relative!r}")
    return destination


def _write(workspace: Path, relative: str, content: str) -> None:
    rendered = dedent(content).lstrip("\n")
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    _target(workspace, relative).write_text(rendered, encoding="utf-8", newline="\n")


def _write_json(workspace: Path, relative: str, value: object) -> None:
    _write(workspace, relative, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _provenance(db: Database, payload: dict[str, Any]) -> dict[str, Any]:
    """Bind the pack to the active normalized row, never to arbitrary payload prose."""

    result: dict[str, Any] = dict(_DEFAULT_PROVENANCE)
    result["lookup_status"] = "fallback metadata; active database row unavailable"
    try:
        with db.connect() as connection:
            row = connection.execute(
                """
                SELECT p.project_id,p.slug AS project_slug,p.title AS project_title,
                       p.category AS project_category,
                       p.implementation_language,p.upstream_reference AS external_reference,
                       p.metadata_json,s.source_id,s.name AS source_name,s.path AS source_path,
                       s.upstream_url,s.commit_hash,s.license
                FROM build_projects p
                JOIN sources s ON s.source_id=p.source_id
                WHERE p.project_id=? AND s.is_active=1
                """,
                (PROJECT_ID,),
            ).fetchone()
        if row is not None:
            for key in (
                "project_id",
                "project_slug",
                "project_title",
                "project_category",
                "implementation_language",
                "external_reference",
                "source_id",
                "source_name",
                "source_path",
                "upstream_url",
                "commit_hash",
                "license",
            ):
                if row[key] is not None:
                    result[key] = _clean(row[key])
            try:
                metadata = json.loads(row["metadata_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                metadata = {}
            if isinstance(metadata, dict):
                linked_license = metadata.get("linked_resource_license")
                if linked_license:
                    result["linked_resource_license"] = _clean(linked_license, limit=200)
                provenance = metadata.get("provenance")
                if isinstance(provenance, dict):
                    source_file = _clean(provenance.get("source_file", "README.md"), limit=300)
                    source_line = _clean(provenance.get("source_line", ""), limit=30)
                    result["source_reference"] = (
                        f"{source_file}:{source_line}" if source_line else source_file
                    )
            result["lookup_status"] = "active database catalog row"
    except sqlite3.Error as error:
        result["lookup_status"] = f"database lookup unavailable: {_clean(error, limit=300)}"
    if payload.get("job_id"):
        result["job_id"] = _clean(payload["job_id"], limit=300)
    return {
        "catalog_source": result,
        "derivation": {
            "source_derived": [
                "catalog title, category, language tag, and upstream link",
            ],
            "agent_generated": [
                "Sprig language contract and all code, tests, exercises, and prose in this pack",
            ],
            "measured": [
                "benchmark and fuzz reports only after their validator commands execute",
            ],
            "inferred": [
                "concept tags, difficulty, curriculum placement, production gaps, and architecture comparison",
            ],
        },
        "license_boundary": (
            "CC0-1.0 covers the Build Your Own X catalog repository metadata only. "
            "The linked article is referenced, not mirrored, and remains NOASSERTION. "
            "This independently generated pack is for personal educational use."
        ),
        "network_used_during_generation": False,
        "linked_content_copied": False,
    }


_MODEL = r'''
    from __future__ import annotations

    from dataclasses import dataclass
    from typing import TypeAlias


    class LanguageError(Exception):
        pass


    class LexError(LanguageError):
        pass


    class ParseError(LanguageError):
        pass


    class CompileError(LanguageError):
        pass


    class RuntimeFault(LanguageError):
        pass


    class ResourceLimit(RuntimeFault):
        pass


    @dataclass(frozen=True)
    class Token:
        kind: str
        lexeme: str
        line: int
        column: int


    @dataclass(frozen=True)
    class Literal:
        value: int


    @dataclass(frozen=True)
    class Variable:
        name: str


    @dataclass(frozen=True)
    class Unary:
        operator: str
        right: "Expr"


    @dataclass(frozen=True)
    class Binary:
        left: "Expr"
        operator: str
        right: "Expr"


    Expr: TypeAlias = Literal | Variable | Unary | Binary


    @dataclass(frozen=True)
    class Let:
        name: str
        initializer: Expr


    @dataclass(frozen=True)
    class Assign:
        name: str
        value: Expr


    @dataclass(frozen=True)
    class Print:
        expression: Expr


    @dataclass(frozen=True)
    class Block:
        statements: tuple["Stmt", ...]


    @dataclass(frozen=True)
    class If:
        condition: Expr
        then_branch: Block
        else_branch: Block | None


    @dataclass(frozen=True)
    class While:
        condition: Expr
        body: Block


    Stmt: TypeAlias = Let | Assign | Print | Block | If | While


    @dataclass(frozen=True)
    class Program:
        statements: tuple[Stmt, ...]


    @dataclass(frozen=True)
    class ExecutionResult:
        outputs: tuple[int, ...]
        globals: dict[str, int]
        steps: int
        engine: str
'''


_LEXER = r'''
    from __future__ import annotations

    from .model import LexError, Token


    KEYWORDS = {
        "let": "LET", "print": "PRINT", "if": "IF", "else": "ELSE",
        "while": "WHILE", "true": "TRUE", "false": "FALSE",
    }
    SINGLE = set("(){};+-*/%")


    def _ascii_letter(character: str) -> bool:
        return "a" <= character <= "z" or "A" <= character <= "Z"


    def _ascii_digit(character: str) -> bool:
        return "0" <= character <= "9"


    def lex(source: str) -> tuple[Token, ...]:
        tokens: list[Token] = []
        index = 0
        line = 1
        column = 1

        def advance() -> str:
            nonlocal index, line, column
            character = source[index]
            index += 1
            if character == "\n":
                line += 1
                column = 1
            else:
                column += 1
            return character

        while index < len(source):
            character = source[index]
            if character in " \t\r\n":
                advance()
                continue
            if character == "/" and index + 1 < len(source) and source[index + 1] == "/":
                while index < len(source) and source[index] != "\n":
                    advance()
                continue
            start_line, start_column = line, column
            if _ascii_digit(character):
                start = index
                while index < len(source) and _ascii_digit(source[index]):
                    advance()
                tokens.append(Token("NUMBER", source[start:index], start_line, start_column))
                continue
            if _ascii_letter(character) or character == "_":
                start = index
                while index < len(source) and (
                    _ascii_letter(source[index]) or _ascii_digit(source[index]) or source[index] == "_"
                ):
                    advance()
                word = source[start:index]
                tokens.append(Token(KEYWORDS.get(word, "IDENT"), word, start_line, start_column))
                continue
            pair = source[index:index + 2]
            if pair in {"==", "!=", "<=", ">=", "&&", "||"}:
                advance(); advance()
                tokens.append(Token(pair, pair, start_line, start_column))
                continue
            if character in SINGLE or character in "=<>!":
                advance()
                tokens.append(Token(character, character, start_line, start_column))
                continue
            raise LexError(f"unexpected character {character!r} at {line}:{column}")
        tokens.append(Token("EOF", "", line, column))
        return tuple(tokens)
'''


_PARSER = r'''
    from __future__ import annotations

    from .lexer import lex
    from .model import Assign, Binary, Block, Expr, If, Let, Literal, ParseError, Print, Program, Token, Unary, Variable, While


    class Parser:
        def __init__(self, tokens: tuple[Token, ...]):
            self.tokens = tokens
            self.current = 0

        def parse(self) -> Program:
            statements = []
            while not self._check("EOF"):
                statements.append(self._statement())
            return Program(tuple(statements))

        def _statement(self):
            if self._match("LET"):
                name = self._consume("IDENT", "expected variable name")
                self._consume("=", "expected '=' after variable name")
                value = self._expression()
                self._consume(";", "expected ';' after declaration")
                return Let(name.lexeme, value)
            if self._match("PRINT"):
                value = self._expression()
                self._consume(";", "expected ';' after value")
                return Print(value)
            if self._match("IF"):
                self._consume("(", "expected '(' after if")
                condition = self._expression()
                self._consume(")", "expected ')' after condition")
                then_branch = self._block()
                else_branch = self._block() if self._match("ELSE") else None
                return If(condition, then_branch, else_branch)
            if self._match("WHILE"):
                self._consume("(", "expected '(' after while")
                condition = self._expression()
                self._consume(")", "expected ')' after condition")
                return While(condition, self._block())
            if self._check("{"):
                return self._block()
            if self._check("IDENT") and self._check_next("="):
                name = self._advance().lexeme
                self._advance()
                value = self._expression()
                self._consume(";", "expected ';' after assignment")
                return Assign(name, value)
            token = self._peek()
            raise ParseError(f"expected statement at {token.line}:{token.column}")

        def _block(self) -> Block:
            self._consume("{", "expected '{'")
            statements = []
            while not self._check("}") and not self._check("EOF"):
                statements.append(self._statement())
            self._consume("}", "expected '}' after block")
            return Block(tuple(statements))

        def _expression(self) -> Expr:
            return self._or()

        def _or(self) -> Expr:
            expression = self._and()
            while self._match("||"):
                expression = Binary(expression, self._previous().kind, self._and())
            return expression

        def _and(self) -> Expr:
            expression = self._equality()
            while self._match("&&"):
                expression = Binary(expression, self._previous().kind, self._equality())
            return expression

        def _equality(self) -> Expr:
            expression = self._comparison()
            while self._match("==", "!="):
                expression = Binary(expression, self._previous().kind, self._comparison())
            return expression

        def _comparison(self) -> Expr:
            expression = self._term()
            while self._match("<", "<=", ">", ">="):
                expression = Binary(expression, self._previous().kind, self._term())
            return expression

        def _term(self) -> Expr:
            expression = self._factor()
            while self._match("+", "-"):
                operator = self._previous().kind
                right = self._factor()
                expression = Binary(expression, operator, right)
            return expression

        def _factor(self) -> Expr:
            expression = self._unary()
            while self._match("*", "/", "%"):
                expression = Binary(expression, self._previous().kind, self._unary())
            return expression

        def _unary(self) -> Expr:
            if self._match("!", "-"):
                return Unary(self._previous().kind, self._unary())
            return self._primary()

        def _primary(self) -> Expr:
            if self._match("NUMBER"):
                token = self._previous()
                significant = token.lexeme.lstrip("0") or "0"
                if len(significant) > 19:
                    raise ParseError(f"integer literal exceeds signed 64-bit magnitude at {token.line}:{token.column}")
                try:
                    value = int(significant)
                except ValueError as error:
                    raise ParseError(f"invalid integer literal at {token.line}:{token.column}") from error
                # INT_MAX + 1 is admitted only so unary minus can spell INT_MIN. All other
                # uses are rejected by checked guest-language evaluation, never host int limits.
                if value > 2 ** 63:
                    raise ParseError(f"integer literal exceeds signed 64-bit magnitude at {token.line}:{token.column}")
                return Literal(value)
            if self._match("TRUE"):
                return Literal(1)
            if self._match("FALSE"):
                return Literal(0)
            if self._match("IDENT"):
                return Variable(self._previous().lexeme)
            if self._match("("):
                expression = self._expression()
                self._consume(")", "expected ')' after expression")
                return expression
            token = self._peek()
            raise ParseError(f"expected expression at {token.line}:{token.column}")

        def _match(self, *kinds: str) -> bool:
            if any(self._check(kind) for kind in kinds):
                self._advance()
                return True
            return False

        def _consume(self, kind: str, message: str) -> Token:
            if self._check(kind):
                return self._advance()
            token = self._peek()
            raise ParseError(f"{message} at {token.line}:{token.column}")

        def _check(self, kind: str) -> bool:
            return self._peek().kind == kind

        def _check_next(self, kind: str) -> bool:
            return self.current + 1 < len(self.tokens) and self.tokens[self.current + 1].kind == kind

        def _advance(self) -> Token:
            token = self._peek()
            if token.kind != "EOF":
                self.current += 1
            return token

        def _peek(self) -> Token:
            return self.tokens[self.current]

        def _previous(self) -> Token:
            return self.tokens[self.current - 1]


    def parse(source: str) -> Program:
        return Parser(lex(source)).parse()
'''


_SEMANTICS = r'''
    from __future__ import annotations

    from .model import RuntimeFault


    INT_MIN = -(2 ** 63)
    INT_MAX = 2 ** 63 - 1


    def checked(value: int) -> int:
        if value < INT_MIN or value > INT_MAX:
            raise RuntimeFault("signed 64-bit integer overflow")
        return value


    def truth(value: int) -> int:
        return int(value != 0)


    def trunc_div(left: int, right: int) -> int:
        if right == 0:
            raise RuntimeFault("division by zero")
        if left == INT_MIN and right == -1:
            raise RuntimeFault("signed 64-bit integer overflow")
        quotient = abs(left) // abs(right)
        return -quotient if (left < 0) != (right < 0) else quotient


    def binary(operator: str, left: int, right: int) -> int:
        if operator == "+": return checked(left + right)
        if operator == "-": return checked(left - right)
        if operator == "*": return checked(left * right)
        if operator == "/": return trunc_div(left, right)
        if operator == "%": return left - trunc_div(left, right) * right
        if operator == "==": return int(left == right)
        if operator == "!=": return int(left != right)
        if operator == "<": return int(left < right)
        if operator == "<=": return int(left <= right)
        if operator == ">": return int(left > right)
        if operator == ">=": return int(left >= right)
        raise RuntimeFault(f"unknown binary operator: {operator}")
'''


_COMPILER = r'''
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
'''


_VM = r'''
    from __future__ import annotations

    from .compiler import BytecodeProgram, Instruction
    from .model import ExecutionResult, ResourceLimit, RuntimeFault
    from .semantics import binary, checked, truth


    BINARY_OPS = {
        "ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "MOD": "%",
        "EQ": "==", "NE": "!=", "LT": "<", "LE": "<=", "GT": ">", "GE": ">=",
    }
    NO_OPERAND = {"TICK", "PRINT", "NEG", "NOT", "BOOL", *BINARY_OPS, "HALT"}
    NAME_OPERAND = {"LOAD", "DEFINE", "STORE"}
    JUMP_OPS = {"JUMP", "JUMP_IF_FALSE", "JUMP_IF_TRUE"}
    MAX_INSTRUCTIONS = 100_000


    def _valid_name(value: object) -> bool:
        if type(value) is not str or not value:
            return False
        first, rest = value[0], value[1:]
        letter = lambda character: "a" <= character <= "z" or "A" <= character <= "Z"
        digit = lambda character: "0" <= character <= "9"
        return (letter(first) or first == "_") and all(
            letter(character) or digit(character) or character == "_" for character in rest
        )


    def verify(program: BytecodeProgram) -> None:
        """Validate an untrusted bytecode graph before executing any instruction."""

        if type(program) is not BytecodeProgram or type(program.instructions) is not tuple:
            raise RuntimeFault("malformed bytecode program")
        instructions = program.instructions
        if not instructions:
            raise RuntimeFault("bytecode program must contain HALT")
        if len(instructions) > MAX_INSTRUCTIONS:
            raise ResourceLimit(f"bytecode exceeds {MAX_INSTRUCTIONS} instructions")
        known = {"CONST", *NAME_OPERAND, *NO_OPERAND, *JUMP_OPS}
        for index, instruction in enumerate(instructions):
            if type(instruction) is not Instruction or type(instruction.opcode) is not str:
                raise RuntimeFault(f"malformed instruction at {index}")
            opcode, operand = instruction.opcode, instruction.operand
            if opcode not in known:
                raise RuntimeFault(f"unknown opcode at {index}: {opcode}")
            if opcode == "CONST" and type(operand) is not int:
                raise RuntimeFault(f"CONST requires an integer operand at {index}")
            if opcode in NAME_OPERAND and not _valid_name(operand):
                raise RuntimeFault(f"{opcode} requires an ASCII identifier at {index}")
            if opcode in NO_OPERAND and operand is not None:
                raise RuntimeFault(f"{opcode} does not accept an operand at {index}")
            if opcode in JUMP_OPS and (
                type(operand) is not int or not 0 <= operand < len(instructions)
            ):
                raise RuntimeFault(f"invalid jump target at {index}: {operand}")
        if instructions[-1].opcode != "HALT":
            raise RuntimeFault("bytecode program must end with HALT")

        incoming_depth = {0: 0}
        pending = [0]
        while pending:
            index = pending.pop()
            depth = incoming_depth[index]
            instruction = instructions[index]
            opcode = instruction.opcode
            required, change = 0, 0
            if opcode in {"CONST", "LOAD"}: change = 1
            elif opcode in {"DEFINE", "STORE", "PRINT"}: required, change = 1, -1
            elif opcode in {"NEG", "NOT", "BOOL"}: required = 1
            elif opcode in BINARY_OPS: required, change = 2, -1
            elif opcode in {"JUMP_IF_FALSE", "JUMP_IF_TRUE"}: required, change = 1, -1
            if depth < required:
                raise RuntimeFault(f"bytecode stack underflow at {index}")
            next_depth = depth + change
            if opcode == "HALT":
                if depth:
                    raise RuntimeFault(f"non-empty stack at HALT ({depth} values)")
                successors: tuple[int, ...] = ()
            elif opcode == "JUMP":
                successors = (instruction.operand,)  # type: ignore[assignment]
            elif opcode in {"JUMP_IF_FALSE", "JUMP_IF_TRUE"}:
                successors = (index + 1, instruction.operand)  # type: ignore[assignment]
            else:
                successors = (index + 1,)
            for successor in successors:
                if not 0 <= successor < len(instructions):
                    raise RuntimeFault(f"program counter can escape after {index}")
                previous = incoming_depth.get(successor)
                if previous is not None and previous != next_depth:
                    raise RuntimeFault(
                        f"inconsistent stack height at {successor}: {previous} versus {next_depth}"
                    )
                if previous is None:
                    incoming_depth[successor] = next_depth
                    pending.append(successor)
        if len(incoming_depth) != len(instructions):
            unreachable = next(index for index in range(len(instructions)) if index not in incoming_depth)
            raise RuntimeFault(f"unreachable bytecode instruction at {unreachable}")


    def execute(program: BytecodeProgram, *, max_steps: int = 10_000) -> ExecutionResult:
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        verify(program)
        stack: list[int] = []
        environment: dict[str, int] = {}
        outputs: list[int] = []
        pc = 0
        steps = 0
        dispatches = 0
        dispatch_limit = len(program.instructions) + max_steps * 16 + 16

        def pop() -> int:
            if not stack:
                raise RuntimeFault("bytecode stack underflow")
            return stack.pop()

        while 0 <= pc < len(program.instructions):
            if dispatches >= dispatch_limit:
                raise ResourceLimit("bytecode dispatch safety budget exceeded")
            instruction = program.instructions[pc]
            dispatches += 1
            pc += 1
            opcode, operand = instruction.opcode, instruction.operand
            if opcode == "TICK":
                if steps >= max_steps:
                    raise ResourceLimit(f"evaluation budget exceeded ({max_steps})")
                steps += 1
            elif opcode == "CONST":
                stack.append(checked(operand))
            elif opcode == "LOAD":
                if operand not in environment:
                    raise RuntimeFault(f"undefined variable: {operand}")
                stack.append(environment[operand])
            elif opcode == "DEFINE":
                if operand in environment: raise RuntimeFault(f"duplicate variable: {operand}")
                environment[operand] = pop()
            elif opcode == "STORE":
                if operand not in environment:
                    raise RuntimeFault(f"undefined variable: {operand}")
                environment[operand] = pop()
            elif opcode == "PRINT":
                outputs.append(pop())
            elif opcode == "NEG":
                stack.append(checked(-pop()))
            elif opcode == "NOT":
                stack.append(int(pop() == 0))
            elif opcode == "BOOL":
                stack.append(truth(pop()))
            elif opcode in BINARY_OPS:
                right, left = pop(), pop()
                stack.append(binary(BINARY_OPS[opcode], left, right))
            elif opcode in {"JUMP", "JUMP_IF_FALSE", "JUMP_IF_TRUE"}:
                take = opcode == "JUMP"
                if opcode == "JUMP_IF_FALSE": take = pop() == 0
                if opcode == "JUMP_IF_TRUE": take = pop() != 0
                if take: pc = operand
            elif opcode == "HALT":
                if stack: raise RuntimeFault("non-empty stack at HALT")
                return ExecutionResult(tuple(outputs), dict(environment), steps, "bytecode")
            else:
                raise RuntimeFault(f"unknown opcode: {opcode}")
        raise RuntimeFault("program counter escaped without HALT")
'''


_INTERPRETER = r'''
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
'''


_BYTECODE_API = r'''
    from __future__ import annotations

    from .compiler import compile_program
    from .model import CompileError, ExecutionResult, LanguageError, LexError, ParseError, ResourceLimit, RuntimeFault
    from .parser import parse
    from .vm import execute

    ENGINE = "bytecode"


    def parse_source(source: str):
        if not isinstance(source, str): raise TypeError("source must be str")
        return parse(source)


    def run_source(source: str, *, max_steps: int = 10_000) -> ExecutionResult:
        return execute(compile_program(parse_source(source)), max_steps=max_steps)
'''


_TREE_API = r'''
    from __future__ import annotations

    from .interpreter import execute
    from .model import CompileError, ExecutionResult, LanguageError, LexError, ParseError, ResourceLimit, RuntimeFault
    from .parser import parse

    ENGINE = "treewalk"


    def parse_source(source: str):
        if not isinstance(source, str): raise TypeError("source must be str")
        return parse(source)


    def run_source(source: str, *, max_steps: int = 10_000) -> ExecutionResult:
        return execute(parse_source(source), max_steps=max_steps)
'''


_INIT = r'''
    from .api import ENGINE, parse_source, run_source
    from .model import CompileError, ExecutionResult, LanguageError, LexError, ParseError, ResourceLimit, RuntimeFault

    __all__ = [
        "ENGINE", "ExecutionResult", "LanguageError", "LexError", "ParseError",
        "CompileError", "RuntimeFault", "ResourceLimit", "parse_source", "run_source",
    ]
'''


_MAIN = r'''
    from __future__ import annotations

    import argparse
    import json
    import sys

    from . import LanguageError, run_source


    def main() -> int:
        parser = argparse.ArgumentParser(description="run a Sprig program")
        parser.add_argument("path", help="source file or - for stdin")
        parser.add_argument("--max-steps", type=int, default=10_000)
        arguments = parser.parse_args()
        source = sys.stdin.read() if arguments.path == "-" else open(arguments.path, encoding="utf-8").read()
        try:
            result = run_source(source, max_steps=arguments.max_steps)
        except (LanguageError, ValueError) as error:
            print(str(error), file=sys.stderr)
            return 2
        print(json.dumps({"engine": result.engine, "outputs": result.outputs, "globals": result.globals, "steps": result.steps}, sort_keys=True))
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_STARTER_MODEL = r'''
    from __future__ import annotations

    from dataclasses import dataclass


    class LanguageError(Exception): pass
    class LexError(LanguageError): pass
    class ParseError(LanguageError): pass
    class CompileError(LanguageError): pass
    class RuntimeFault(LanguageError): pass
    class ResourceLimit(RuntimeFault): pass


    @dataclass(frozen=True)
    class ExecutionResult:
        outputs: tuple[int, ...]
        globals: dict[str, int]
        steps: int
        engine: str
'''


_STARTER_LEXER = r'''
    from __future__ import annotations

    from dataclasses import dataclass


    @dataclass(frozen=True)
    class Token:
        kind: str
        lexeme: str
        line: int
        column: int


    def lex(source: str) -> tuple[Token, ...]:
        # TODO(stage 1a): emit located tokens and one EOF token; reject unknown characters.
        raise NotImplementedError("implement lex")
'''


_STARTER_PARSER = r'''
    from __future__ import annotations

    from .lexer import Token


    def parse(tokens: tuple[Token, ...]):
        # TODO(stage 1b): define immutable AST nodes and implement the documented precedence ladder.
        raise NotImplementedError("implement parse")
'''


_STARTER_COMPILER = r'''
    from __future__ import annotations

    from dataclasses import dataclass


    @dataclass(frozen=True)
    class Instruction:
        opcode: str
        operand: int | str | None = None


    @dataclass(frozen=True)
    class BytecodeProgram:
        instructions: tuple[Instruction, ...]


    def compile_program(program) -> BytecodeProgram:
        # TODO(stage 2): emit stack-balanced instructions and patch structured control flow.
        raise NotImplementedError("implement compile_program")
'''


_STARTER_VM = r'''
    from __future__ import annotations

    from .compiler import BytecodeProgram
    from .model import ExecutionResult


    def execute(program: BytecodeProgram, *, max_steps: int) -> ExecutionResult:
        # TODO(stage 3): validate operands, enforce max_steps, and execute without host eval/exec.
        raise NotImplementedError("implement execute")
'''


_STARTER_API = r'''
    from __future__ import annotations

    from .compiler import compile_program
    from .lexer import lex
    from .model import CompileError, ExecutionResult, LanguageError, LexError, ParseError, ResourceLimit, RuntimeFault
    from .parser import parse
    from .vm import execute

    ENGINE = "learner-bytecode"


    def parse_source(source: str):
        if not isinstance(source, str): raise TypeError("source must be str")
        return parse(lex(source))


    def run_source(source: str, *, max_steps: int = 10_000) -> ExecutionResult:
        return execute(compile_program(parse_source(source)), max_steps=max_steps)
'''


_PUBLIC_TESTS = r'''
    from __future__ import annotations

    import unittest

    import tinyvm


    class PublicContractTests(unittest.TestCase):
        def test_arithmetic_precedence_and_left_associativity(self) -> None:
            result = tinyvm.run_source("print 2 + 3 * 4; print 20 - 5 - 3;")
            self.assertEqual((14, 12), result.outputs)

        def test_state_loop_and_branch(self) -> None:
            source = """
                let total = 0;
                let n = 5;
                while (n > 0) { total = total + n; n = n - 1; }
                if (total == 15) { print total; } else { print 0; }
            """
            result = tinyvm.run_source(source)
            self.assertEqual((15,), result.outputs)
            self.assertEqual({"n": 0, "total": 15}, result.globals)
            self.assertGreater(result.steps, 0)

        def test_boolean_results_and_short_circuit(self) -> None:
            result = tinyvm.run_source("print false && (1 / 0); print true || missing;")
            self.assertEqual((0, 1), result.outputs)

        def test_comments_and_unary(self) -> None:
            result = tinyvm.run_source("// ignored\nprint -(2 + 3); print !0;")
            self.assertEqual((-5, 1), result.outputs)

        def test_errors_are_typed(self) -> None:
            with self.assertRaises(tinyvm.ParseError):
                tinyvm.run_source("print 1")
            with self.assertRaises(tinyvm.RuntimeFault):
                tinyvm.run_source("print unknown;")

        def test_budget_bounds_nontermination(self) -> None:
            with self.assertRaises(tinyvm.ResourceLimit):
                tinyvm.run_source("while (true) { print 1; }", max_steps=25)


    if __name__ == "__main__":
        unittest.main()
'''


_HIDDEN_TESTS = r'''
    from __future__ import annotations

    import unittest

    import tinyvm


    class WithheldContractTests(unittest.TestCase):
        def test_negative_division_and_remainder_truncate_toward_zero(self) -> None:
            result = tinyvm.run_source("print -7 / 3; print -7 % 3; print 7 % -3;")
            self.assertEqual((-2, -1, 1), result.outputs)

        def test_logical_precedence(self) -> None:
            result = tinyvm.run_source("print true || false && false; print 1 < 2 == true;")
            self.assertEqual((1, 1), result.outputs)

        def test_duplicate_declaration_and_assignment_before_declaration(self) -> None:
            with self.assertRaises(tinyvm.RuntimeFault):
                tinyvm.run_source("let x = 1; let x = 2;")
            with self.assertRaises(tinyvm.RuntimeFault):
                tinyvm.run_source("x = 2;")

        def test_overflow_is_not_host_integer_growth(self) -> None:
            with self.assertRaisesRegex(tinyvm.RuntimeFault, "overflow"):
                tinyvm.run_source("print 9223372036854775807 + 1;")

        def test_signed_minimum_literal_and_bounded_integer_diagnostics(self) -> None:
            self.assertEqual((-9223372036854775808,), tinyvm.run_source("print -9223372036854775808;").outputs)
            huge = "print " + "9" * 5_000 + ";"
            with self.assertRaisesRegex(tinyvm.ParseError, r"64-bit magnitude at 1:7"):
                tinyvm.run_source(huge)

        def test_documented_ascii_lexical_contract(self) -> None:
            for source in ("print ١;", "let café = 1;", "print ²;"):
                with self.subTest(source=source), self.assertRaises(tinyvm.LexError):
                    tinyvm.run_source(source)

        def test_error_order_and_budget_are_architecture_neutral(self) -> None:
            with self.assertRaisesRegex(tinyvm.RuntimeFault, "division by zero"):
                tinyvm.run_source("let x = 1; let x = 1 / 0;")
            with self.assertRaisesRegex(tinyvm.RuntimeFault, "division by zero"):
                tinyvm.run_source("x = 1 / 0;")
            result = tinyvm.run_source("print 1;", max_steps=2)
            self.assertEqual((1,), result.outputs)
            self.assertEqual(2, result.steps)
            with self.assertRaises(tinyvm.ResourceLimit):
                tinyvm.run_source("print 1;", max_steps=1)

        def test_else_is_not_executed_after_true_branch(self) -> None:
            result = tinyvm.run_source("if (2) { print 7; } else { print 1 / 0; }")
            self.assertEqual((7,), result.outputs)

        def test_diagnostics_carry_location(self) -> None:
            with self.assertRaisesRegex(tinyvm.LexError, r"2:1"):
                tinyvm.run_source("print 1;\n@")

        def test_invalid_budget_rejected_before_execution(self) -> None:
            for value in (0, -1, True):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    tinyvm.run_source("print 1;", max_steps=value)


    if __name__ == "__main__":
        unittest.main()
'''


_BYTECODE_TESTS = r'''
    from __future__ import annotations

    import unittest

    from tinyvm.compiler import compile_program
    from tinyvm.parser import parse
    from tinyvm.vm import execute


    class BytecodeContractTests(unittest.TestCase):
        def test_control_flow_targets_are_resolved_and_in_range(self) -> None:
            program = compile_program(parse("let x = 2; while (x) { x = x - 1; } print x;"))
            for instruction in program.instructions:
                if instruction.opcode.startswith("JUMP"):
                    self.assertIsInstance(instruction.operand, int)
                    self.assertGreaterEqual(instruction.operand, 0)
                    self.assertLess(instruction.operand, len(program.instructions))
            self.assertEqual((0,), execute(program).outputs)

        def test_compiler_emits_halt_and_vm_rejects_unknown_opcode(self) -> None:
            from tinyvm.compiler import BytecodeProgram, Instruction
            from tinyvm.model import RuntimeFault
            program = compile_program(parse("print 1;"))
            self.assertEqual("HALT", program.instructions[-1].opcode)
            with self.assertRaisesRegex(RuntimeFault, "unknown opcode"):
                execute(BytecodeProgram((Instruction("MYSTERY"), Instruction("HALT"))))

        def test_verifier_rejects_malformed_operands_and_instructions(self) -> None:
            from tinyvm.compiler import BytecodeProgram, Instruction
            from tinyvm.model import RuntimeFault
            malformed = (
                ("boolean CONST", (Instruction("CONST", True), Instruction("PRINT"), Instruction("HALT"))),
                ("boolean jump", (Instruction("JUMP", True), Instruction("HALT"))),
                ("spurious operand", (Instruction("HALT", "ignored"),)),
                ("raw object", (object(),)),
                ("stack underflow", (Instruction("PRINT"), Instruction("HALT"))),
                ("unreachable instruction", (Instruction("JUMP", 1), Instruction("HALT"), Instruction("HALT"))),
                (
                    "inconsistent join",
                    (
                        Instruction("CONST", 1), Instruction("JUMP_IF_FALSE", 3),
                        Instruction("CONST", 2), Instruction("HALT"),
                    ),
                ),
            )
            for name, instructions in malformed:
                with self.subTest(name=name), self.assertRaises(RuntimeFault):
                    execute(BytecodeProgram(instructions))

        def test_compiler_metering_matches_source_semantics(self) -> None:
            program = compile_program(parse("print 1;"))
            self.assertEqual(2, [item.opcode for item in program.instructions].count("TICK"))
            self.assertEqual(2, execute(program, max_steps=2).steps)

        def test_short_circuit_has_branch_not_eager_boolean_opcode(self) -> None:
            program = compile_program(parse("print false && missing;"))
            opcodes = [instruction.opcode for instruction in program.instructions]
            self.assertIn("JUMP_IF_FALSE", opcodes)
            self.assertEqual((0,), execute(program).outputs)


    if __name__ == "__main__":
        unittest.main()
'''


_SYNTAX_CHECKER = r'''
    from __future__ import annotations

    import sys
    from pathlib import Path


    def main() -> int:
        failures = []
        for path in sorted(Path(".").rglob("*.py")):
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except (OSError, SyntaxError, UnicodeError) as error:
                failures.append(f"{path}: {error}")
        if failures:
            print("\n".join(failures), file=sys.stderr)
            return 1
        print(f"compiled {len(list(Path('.').rglob('*.py')))} Python sources")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_BOUNDARY_CHECKER = r'''
    from __future__ import annotations

    import sys
    from pathlib import Path


    def main() -> int:
        visible = [Path("README.md"), Path("REQUIREMENTS.md"), Path("GRAMMAR.md"), Path("BYTECODE.md"), Path("CONCEPTS.md"), Path("DESIGN_QUESTIONS.md")]
        visible += sorted(Path("starter").rglob("*")) + sorted(Path("public_tests").rglob("*"))
        forbidden = ("sealed/", "EXPECTED_REVIEW", "root-cause.md", "patch.diff", "WithheldContractTests")
        leaks = []
        expected_starter = {
            Path("starter/README.md"),
            *(Path("starter/tinyvm") / name for name in (
                "__init__.py", "api.py", "compiler.py", "lexer.py", "model.py", "parser.py", "vm.py",
            )),
        }
        expected_public = {Path("public_tests/test_public.py")}
        actual_starter = {path for path in Path("starter").rglob("*") if path.is_file()}
        actual_public = {path for path in Path("public_tests").rglob("*") if path.is_file()}
        for path in sorted(expected_starter - actual_starter):
            leaks.append(f"missing learner-visible file: {path}")
        for path in sorted(actual_starter - expected_starter):
            leaks.append(f"unexpected learner-visible file: {path}")
        for path in sorted(expected_public - actual_public):
            leaks.append(f"missing public-test file: {path}")
        for path in sorted(actual_public - expected_public):
            leaks.append(f"unexpected public-test file: {path}")
        for path in visible:
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for marker in forbidden:
                    if marker in text:
                        leaks.append(f"{path}: leaked marker {marker!r}")
        starter = "\n".join(path.read_text(encoding="utf-8") for path in sorted(Path("starter/tinyvm").glob("*.py")))
        for stage in ("TODO(stage 1a)", "TODO(stage 1b)", "TODO(stage 2)", "TODO(stage 3)"):
            if stage not in starter:
                leaks.append(f"starter is missing progressive marker {stage}")
        if "NotImplementedError" not in starter:
            leaks.append("starter unexpectedly contains a completed implementation")
        if leaks:
            print("\n".join(leaks), file=sys.stderr)
            return 1
        print("learner-visible starter and public tests omit withheld paths and answer markers")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_STARTER_CHECKER = r'''
    from __future__ import annotations

    import tinyvm


    try:
        tinyvm.run_source("print 1;")
    except NotImplementedError:
        print("starter is importable and intentionally incomplete")
        raise SystemExit(0)
    raise SystemExit("starter must not contain the sealed implementation")
'''


_BATCH_RUNNER = r'''
    from __future__ import annotations

    import json
    import sys

    import tinyvm


    programs = json.load(sys.stdin)
    results = []
    for source in programs:
        result = tinyvm.run_source(source, max_steps=20_000)
        results.append({"outputs": result.outputs, "globals": result.globals})
    json.dump({"engine": tinyvm.ENGINE, "results": results}, sys.stdout, sort_keys=True)
'''


_FUZZER = r'''
    from __future__ import annotations

    import argparse
    import hashlib
    import json
    import os
    import random
    import subprocess
    import sys
    from pathlib import Path


    OPS = ("+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=", "&&", "||")


    def trunc_div(left: int, right: int) -> int:
        quotient = abs(left) // abs(right)
        return -quotient if (left < 0) != (right < 0) else quotient


    def literal(value: int) -> str:
        return str(value) if value >= 0 else f"-{abs(value)}"


    def expression(randomizer: random.Random, depth: int) -> tuple[str, int]:
        if depth <= 0 or randomizer.random() < 0.30:
            value = randomizer.randint(-12, 12)
            return literal(value), value
        if randomizer.random() < 0.18:
            source, value = expression(randomizer, depth - 1)
            if randomizer.choice((True, False)):
                return f"(-({source}))", -value
            return f"(!({source}))", int(value == 0)
        left_source, left = expression(randomizer, depth - 1)
        right_source, right = expression(randomizer, depth - 1)
        operator = randomizer.choice(OPS)
        if operator in {"/", "%"} and right == 0:
            right_source, right = "1", 1
        if operator == "+": value = left + right
        elif operator == "-": value = left - right
        elif operator == "*": value = left * right
        elif operator == "/": value = trunc_div(left, right)
        elif operator == "%": value = left - trunc_div(left, right) * right
        elif operator == "<": value = int(left < right)
        elif operator == "<=": value = int(left <= right)
        elif operator == ">": value = int(left > right)
        elif operator == ">=": value = int(left >= right)
        elif operator == "==": value = int(left == right)
        elif operator == "!=": value = int(left != right)
        elif operator == "&&": value = int(left != 0 and right != 0)
        else: value = int(left != 0 or right != 0)
        return f"({left_source} {operator} {right_source})", value


    def invoke(path: str, programs: list[str]) -> dict[str, object]:
        environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": path}
        process = subprocess.run(
            [sys.executable, "adversarial/batch_runner.py"],
            input=json.dumps(programs), text=True, capture_output=True,
            env=environment, timeout=30, check=False,
        )
        if process.returncode:
            raise RuntimeError(f"engine {path} failed: {process.stderr[-500:]}")
        return json.loads(process.stdout)


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--seed", type=int, default=7401)
        parser.add_argument("--iterations", type=int, default=120)
        parser.add_argument("--output", required=True)
        arguments = parser.parse_args()
        if not 1 <= arguments.iterations <= 500:
            raise SystemExit("iterations must be in [1, 500]")
        randomizer = random.Random(arguments.seed)
        programs, expected = [], []
        for _ in range(arguments.iterations):
            start = randomizer.randint(0, 8)
            scale = randomizer.randint(-6, 6)
            divisor = randomizer.choice(tuple(value for value in range(-7, 8) if value))
            expression_source, expression_value = expression(randomizer, 4)
            total = scale * start * (start + 1) // 2
            quotient = trunc_div(total, divisor)
            remainder = total - quotient * divisor
            programs.append(
                f"""// deterministic generated stateful case
                let n = {start}; let total = 0; let scale = {literal(scale)};
                while (n > 0) {{ total = total + scale * n; n = n - 1; }}
                print total; print total / {literal(divisor)}; print total % {literal(divisor)};
                if ((total > 0 && n == 0) || false) {{ print 1; }} else {{ print 0; }}
                print false && (1 / 0); print true || missing; print {expression_source};
                """
            )
            expected.append(
                {
                    "outputs": [total, quotient, remainder, int(total > 0), 0, 1, expression_value],
                    "globals": {"n": 0, "scale": scale, "total": total},
                }
            )
        bytecode = invoke("sealed/reference", programs)
        treewalk = invoke("alternatives/treewalk", programs)
        if bytecode["results"] != expected or treewalk["results"] != expected:
            print("differential/oracle mismatch", file=sys.stderr)
            return 1
        output = Path(arguments.output)
        allowed = (Path.cwd() / "reports").resolve()
        try: output.resolve().relative_to(allowed)
        except ValueError: raise SystemExit("output must remain under reports/")
        output.parent.mkdir(parents=True, exist_ok=True)
        corpus = json.dumps(programs, separators=(",", ":"), ensure_ascii=True).encode()
        report = {
            "schema_version": 1, "seed": arguments.seed, "iterations": arguments.iterations,
            "corpus_sha256": hashlib.sha256(corpus).hexdigest(),
            "engines": [bytecode["engine"], treewalk["engine"]],
            "properties": ["independent arithmetic oracle", "cross-architecture agreement", "deterministic stateful grammar corpus"],
            "coverage": {
                "programs": arguments.iterations,
                "features": [
                    "declarations", "assignment", "while", "if/else", "comments",
                    "division/remainder", "unary", "comparison", "short-circuit",
                ],
            },
            "failures": 0,
        }
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"checked {arguments.iterations} deterministic grammar programs; corpus={report['corpus_sha256']}")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_BENCHMARK_WORKER = r'''
    from __future__ import annotations

    import argparse
    import hashlib
    import json
    import os
    import time

    import tinyvm


    SOURCE = """
        let total = 0;
        let n = 120;
        while (n > 0) { total = total + n; n = n - 1; }
        print total;
    """


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--samples", type=int, required=True)
        arguments = parser.parse_args()
        if not 3 <= arguments.samples <= 50:
            raise SystemExit("samples must be in [3, 50]")
        for _ in range(3):
            result = tinyvm.run_source(SOURCE, max_steps=20_000)
        raw = []
        for _ in range(arguments.samples):
            started = time.perf_counter_ns()
            result = tinyvm.run_source(SOURCE, max_steps=20_000)
            elapsed = time.perf_counter_ns() - started
            if elapsed <= 0: raise SystemExit("non-positive monotonic timing")
            if result.outputs != (7260,): raise SystemExit("workload result mismatch")
            raw.append(elapsed)
        print(json.dumps({
            "engine": tinyvm.ENGINE,
            "pid": os.getpid(),
            "raw_elapsed_ns": raw,
            "sample_output_sha256": hashlib.sha256(repr(result.outputs).encode()).hexdigest(),
            "semantic_steps_last_sample": result.steps,
        }, sort_keys=True))
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_BENCHMARK = r'''
    from __future__ import annotations

    import argparse
    import json
    import os
    import platform
    import statistics
    import subprocess
    import sys
    from pathlib import Path


    IMPLEMENTATIONS = {"bytecode": "sealed/reference", "treewalk": "alternatives/treewalk"}


    def measure(name: str, path: str, samples: int) -> dict[str, object]:
        environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": path}
        process = subprocess.run(
            [sys.executable, "benchmarks/worker.py", "--samples", str(samples)],
            text=True, capture_output=True, env=environment, timeout=30, check=False,
        )
        if process.returncode:
            raise RuntimeError(f"{name} worker failed: {process.stderr[-500:]}")
        value = json.loads(process.stdout)
        if value["engine"] != name: raise RuntimeError("implementation identity mismatch")
        raw = value["raw_elapsed_ns"]
        value["median_elapsed_ns"] = int(statistics.median(raw))
        value["min_elapsed_ns"] = min(raw)
        value["max_elapsed_ns"] = max(raw)
        return value


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--samples", type=int, default=7)
        parser.add_argument("--output", required=True)
        arguments = parser.parse_args()
        if not 3 <= arguments.samples <= 50:
            raise SystemExit("samples must be in [3, 50]")
        output = Path(arguments.output)
        allowed = (Path.cwd() / "benchmarks" / "results").resolve()
        try: output.resolve().relative_to(allowed)
        except ValueError: raise SystemExit("output must remain under benchmarks/results/")
        raw_results = {name: measure(name, path, arguments.samples) for name, path in IMPLEMENTATIONS.items()}
        if len({value["pid"] for value in raw_results.values()}) != 2:
            raise SystemExit("architectures were not measured in separate processes")
        report = {
            "schema_version": 1,
            "hypothesis": "The complete public API paths have measurably different end-to-end costs; no dispatch-only or universal winner is asserted.",
            "measurement_scope": "Each timed run_source call includes lexing and parsing for both engines and compilation for bytecode.",
            "parameters": {"samples_per_architecture": arguments.samples, "warmups": 3, "workload": "sum integers 120 through 1", "fixed_order": ["bytecode", "treewalk"]},
            "environment": {
                "python": sys.version, "executable": sys.executable, "implementation": platform.python_implementation(),
                "platform": platform.platform(), "machine": platform.machine(), "processor": platform.processor(),
                "cpu_count": os.cpu_count(), "clock": "time.perf_counter_ns", "network": "not used",
            },
            "command": [sys.executable, "benchmarks/benchmark.py", "--samples", str(arguments.samples), "--output", arguments.output],
            "raw_results": raw_results,
            "interpretation_boundary": "Fixed order, Python overhead, host load, and compile inclusion limit inference; rerun and use a precompiled benchmark before attributing dispatch cost.",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({name: result["median_elapsed_ns"] for name, result in raw_results.items()}, sort_keys=True))
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_DEBUG_REGRESSION = r'''
    from __future__ import annotations

    import sys

    import tinyvm


    result = tinyvm.run_source("print 20 - 5 - 3;")
    if result.outputs != (12,):
        print(f"subtraction grouped incorrectly: wanted 12, observed {result.outputs}", file=sys.stderr)
        raise SystemExit(1)
    print("subtraction is left-associative: (20 - 5) - 3 == 12")
'''


_DEBUG_INTEGRITY = r'''
    from __future__ import annotations

    from pathlib import Path


    buggy = Path("debugging/parser-associativity/buggy/tinyvm/parser.py").read_text(encoding="utf-8")
    fixed = Path("debugging/parser-associativity/sealed/fixed/tinyvm/parser.py").read_text(encoding="utf-8")
    expected_bug = "right = self._term()"
    expected_fix = "right = self._factor()"
    if buggy.count(expected_bug) != 1 or fixed.count(expected_fix) != 1:
        raise SystemExit("challenge no longer contains the isolated parser mutation")
    normalized = buggy.replace(expected_bug, expected_fix)
    if normalized != fixed:
        raise SystemExit("buggy and fixed parser differ by more than the isolated root cause")
    patch = Path("debugging/parser-associativity/sealed/patch.diff").read_text(encoding="utf-8")
    if "-                right = self._term()" not in patch or "+                right = self._factor()" not in patch:
        raise SystemExit("sealed patch does not describe the proven repair")
    print("isolated mutation and repair patch are structurally consistent")
'''


_PROPOSED_OPTIMIZER = r'''
    from __future__ import annotations

    from tinyvm.model import Binary, Literal, Unary
    from tinyvm.semantics import binary


    def fold(expression):
        if isinstance(expression, Literal):
            return expression
        if isinstance(expression, Unary):
            right = fold(expression.right)
            if isinstance(right, Literal):
                return Literal(-right.value if expression.operator == "-" else int(right.value == 0))
            return Unary(expression.operator, right)
        if isinstance(expression, Binary):
            left = fold(expression.left)
            right = fold(expression.right)
            if isinstance(left, Literal) and isinstance(right, Literal):
                if expression.operator == "&&": return Literal(int(left.value != 0 and right.value != 0))
                if expression.operator == "||": return Literal(int(left.value != 0 or right.value != 0))
                return Literal(binary(expression.operator, left.value, right.value))
            return Binary(left, expression.operator, right)
        return expression
'''


_REVIEW_DEMONSTRATION = r'''
    from __future__ import annotations

    import sys
    from pathlib import Path

    import tinyvm

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "proposed"))
    from optimizer import fold


    source = "print false && (1 / 0);"
    correct = tinyvm.run_source(source)
    if correct.outputs != (0,): raise SystemExit("reference short-circuit baseline failed")
    expression = tinyvm.parse_source(source).statements[0].expression
    try:
        fold(expression)
    except tinyvm.RuntimeFault as error:
        if "division by zero" not in str(error): raise
        print("proposed optimizer eagerly evaluates an unreachable RHS and changes valid-program behavior")
        raise SystemExit(0)
    raise SystemExit("expected optimizer semantic regression did not reproduce")
'''


def _write_implementation(workspace: Path, root: str, *, bytecode: bool) -> None:
    common = {
        "model.py": _MODEL,
        "lexer.py": _LEXER,
        "parser.py": _PARSER,
        "semantics.py": _SEMANTICS,
        "api.py": _BYTECODE_API if bytecode else _TREE_API,
        "__init__.py": _INIT,
        "__main__.py": _MAIN,
    }
    if bytecode:
        common.update({"compiler.py": _COMPILER, "vm.py": _VM})
    else:
        common["interpreter.py"] = _INTERPRETER
    for name, content in common.items():
        _write(workspace, f"{root}/tinyvm/{name}", content)


def _documents(workspace: Path, provenance: dict[str, Any]) -> None:
    _write(
        workspace,
        "README.md",
        r'''
        # Sprig: a bounded language and bytecode VM

        Implement a small imperative language end to end: tokenize text, parse an AST, compile it
        to documented stack bytecode, then execute it under a deterministic instruction budget.
        The exercise is deliberately small enough to understand completely but includes contracts
        that toy interpreters often omit: source locations, short-circuit control flow, checked
        64-bit arithmetic, typed failures, undefined-name handling, and nontermination bounds.

        ## Progressive path

        1. Read `REQUIREMENTS.md`, `GRAMMAR.md`, and `BYTECODE.md` without opening withheld material.
        2. Complete the learner package in `starter` one stage at a time and run `public_tests`.
        3. Write down bytecode and stack-height invariants before implementing jumps.
        4. Run your own malformed-input and resource-budget experiments.
        5. Intentionally reveal the reference and withheld tests, then compare the bytecode engine
           with the independent tree-walk alternative through their common API.
        6. Reproduce the parser debugging incident, review the optimizer proposal, and benchmark
           both architectures on your own host.

        The withheld tree is a progressive-disclosure boundary, not a hardened hostile-user
        sandbox. Make a learner view by copying only the six learner documents, `starter`, and
        `public_tests`. Generated code is educational and explicitly not production-ready.
        ''',
    )
    _write(
        workspace,
        "REQUIREMENTS.md",
        r'''
        # Observable contract

        Export `parse_source(str)` and `run_source(str, *, max_steps=10000)` from `tinyvm`.
        `run_source` returns immutable output values, a snapshot of global variables, a non-negative
        semantic step count, and an engine name. Both supplied architectures obey this API. A step is
        one source AST statement or expression visit in both engines; the same `max_steps` therefore
        has the same success/failure boundary. Bytecode dispatch has a separate internal safety bound.

        Values are signed 64-bit integers; booleans are canonical integers 0 and 1. Arithmetic
        overflow, division by zero, an undefined name, a duplicate `let`, malformed input, and
        exhausted step budgets are typed language errors. Division truncates toward zero and the
        remainder has the dividend's sign. `&&` and `||` short-circuit and return 0 or 1.

        Declarations are global in this intentionally small language. A block controls sequencing,
        not lexical scope. Output is captured rather than printed by the library. The implementation
        may not use Python `eval`, `exec`, or AST compilation as its language engine.

        Suggested milestones: literals/print; precedence and variables; checked operations; branches;
        loops; bytecode validation and resource limits; diagnostics and adversarial tests.
        ''',
    )
    _write(
        workspace,
        "GRAMMAR.md",
        r'''
        # Sprig grammar and precedence

        ```text
        program     := statement* EOF
        statement   := "let" IDENT "=" expression ";"
                     | IDENT "=" expression ";"
                     | "print" expression ";"
                     | "if" "(" expression ")" block ("else" block)?
                     | "while" "(" expression ")" block
                     | block
        block       := "{" statement* "}"
        expression  := or
        or          := and ("||" and)*
        and         := equality ("&&" equality)*
        equality    := comparison (("==" | "!=") comparison)*
        comparison  := term (("<" | "<=" | ">" | ">=") term)*
        term        := factor (("+" | "-") factor)*
        factor      := unary (("*" | "/" | "%") unary)*
        unary       := ("!" | "-") unary | primary
        primary     := NUMBER | "true" | "false" | IDENT | "(" expression ")"
        ```

        Binary precedence rows are left-associative. Identifiers match `[A-Za-z_][A-Za-z0-9_]*`.
        Decimal integers use ASCII digits and have no sign token; unary minus supplies it. The parser
        admits magnitudes through 2^63 so `-9223372036854775808` is representable, while other uses of
        2^63 overflow during evaluation. `//` comments end at newline.
        Diagnostics report one-based line and column at the unexpected token or character.
        ''',
    )
    _write(
        workspace,
        "BYTECODE.md",
        r'''
        # Bytecode contract

        Instructions are immutable `(opcode, operand)` records. `TICK` records one source-level AST
        visit so resource behavior agrees with the tree walker. `CONST`, `LOAD`, arithmetic,
        comparison, `NEG`, `NOT`, and `BOOL` push one value. Binary operations pop right then left.
        `DEFINE`, `STORE`, and `PRINT` consume one value. Conditional jumps consume their condition.
        `JUMP` consumes nothing. `HALT` requires an empty stack.

        | Family | Opcodes | Operand |
        | --- | --- | --- |
        | metering | `TICK` | none |
        | values | `CONST`, `LOAD` | integer or name |
        | state | `DEFINE`, `STORE`, `PRINT` | name, name, none |
        | unary | `NEG`, `NOT`, `BOOL` | none |
        | binary | `ADD SUB MUL DIV MOD EQ NE LT LE GT GE` | none |
        | control | `JUMP JUMP_IF_FALSE JUMP_IF_TRUE` | absolute instruction index |
        | lifecycle | `HALT` | none |

        Only `TICK` consumes a public `max_steps` unit. A separate bounded dispatch guard protects the
        VM from malformed no-progress cycles. Before execution, verification checks instruction and
        operand types, arity, jump targets, reachability, underflow, and stack-height joins. Compilation
        of logical operators uses branches; an eager `AND`/`OR` opcode would violate short circuit.
        ''',
    )
    _write(
        workspace,
        "CONCEPTS.md",
        r'''
        # Concepts to extract

        - A lexer turns characters into located tokens; a parser turns tokens into an AST according
          to precedence and associativity contracts.
        - Compilation linearizes structured control flow. Forward branches require patching while
          stack-height invariants must agree at every control-flow join.
        - An interpreter's dispatch architecture is independent from source-language semantics.
          Differential testing is useful because the tree-walk and bytecode paths fail differently.
        - Host-language behavior is not automatically guest-language behavior. Integer bounds,
          negative division, errors, short circuit, and budgets need explicit definitions.
        - A step limit is a deterministic availability boundary, not a security sandbox.
        ''',
    )
    _write(
        workspace,
        "DESIGN_QUESTIONS.md",
        r'''
        # Design questions

        1. Which layer owns source locations, and how would locations survive into bytecode errors?
        2. State a stack-height invariant for every opcode and control-flow join.
        3. Should `let` inside a branch create a global? What migration supports lexical scope later?
        4. Can a compiler reject all undefined names without rejecting valid control-flow programs?
        5. Which work should consume the resource budget: AST visits, opcodes, allocation, output?
        6. How would closures change environment ownership and instruction representation?
        7. Which differential tests have an independent semantic oracle rather than mere agreement?
        ''',
    )
    _write(
        workspace,
        "TRADEOFFS.md",
        r'''
        # Architecture comparison

        Both implementations use identical model, lexer, parser, and integer-semantics source files
        and expose the same API. The tree walker maps source structure directly onto Python calls, so
        it is compact and easy to instrument with AST locations. Its recursive dispatch and repeated
        tree traversal leave fewer optimization opportunities. The bytecode compiler pays an up-front
        translation cost, makes control flow and stack state explicit, and can cache programs or add
        peephole optimization. Its failure modes include bad patch targets and stack imbalance.

        The benchmark stores raw timings rather than declaring a universal winner. These Python
        implementations compare architecture, not C-vs-Python language performance. The supplied
        smoke benchmark measures the complete public `run_source` path: lexing and parsing for both
        engines, plus compilation for the bytecode engine. It does not isolate dispatch cost.
        ''',
    )
    _write(
        workspace,
        "PRODUCTION_GAPS.md",
        r'''
        # Why this should not ship

        Status: **PARTIAL / NOT_PRODUCTION_READY**. The pack has bounded local validation, not a
        security or compatibility commitment. Missing work includes recursion/nesting limits in the
        parser, memory/output quotas, stable serialized
        bytecode with versioning, Unicode policy, richer location-preserving diagnostics, fuzzing at
        much larger scale, profiler-guided optimization, package signing, and a hostile-input sandbox.
        Python process isolation and `max_steps` do not bound memory or wall time. There is no module
        system, lexical scope, functions, debugger, tracing interface, or backward-compatibility plan.
        ''',
    )
    _write(
        workspace,
        "LICENSE_BOUNDARY.md",
        f'''
        # Provenance and license boundary

        The catalog record is `{provenance["catalog_source"]["project_id"]}` from Build Your Own X
        commit `{provenance["catalog_source"]["commit_hash"]}`. Its catalog metadata is CC0-1.0.
        The external article at `{provenance["catalog_source"]["external_reference"]}` is linked but
        neither fetched nor copied; its license is `{provenance["catalog_source"]["linked_resource_license"]}`.
        All Sprig code, tests, challenge mutations, and explanatory text were independently generated.
        See `PROVENANCE.json` for machine-readable classifications.
        ''',
    )


def _write_supporting_artifacts(workspace: Path) -> None:
    _write(workspace, "public_tests/test_public.py", _PUBLIC_TESTS)
    _write(workspace, "sealed/reference_tests/test_hidden.py", _HIDDEN_TESTS)
    _write(workspace, "sealed/bytecode_tests/test_bytecode.py", _BYTECODE_TESTS)
    _write(workspace, "environment/check_python.py", _SYNTAX_CHECKER)
    _write(workspace, "environment/check_boundaries.py", _BOUNDARY_CHECKER)
    _write(workspace, "environment/check_starter.py", _STARTER_CHECKER)
    _write(workspace, "adversarial/batch_runner.py", _BATCH_RUNNER)
    _write(workspace, "adversarial/grammar_fuzz.py", _FUZZER)
    _write(
        workspace,
        "adversarial/README.md",
        """
        # Deterministic grammar/property fuzzing

        The bounded generator records its seed and corpus hash, computes an independent value oracle,
        and compares both execution architectures across expressions, variables, bounded loops,
        branches, division/remainder, and short circuit. Expand it with malformed syntax and shrinking.
        """,
    )
    _write(workspace, "benchmarks/worker.py", _BENCHMARK_WORKER)
    _write(workspace, "benchmarks/benchmark.py", _BENCHMARK)
    _write(
        workspace,
        "benchmarks/README.md",
        """
        # Benchmark protocol

        Three unrecorded warmups precede raw `perf_counter_ns` samples. Each architecture runs in a
        separate fresh Python process and must produce the same checksum-identified answer. Timings
        cover the public `run_source` path, including lex/parse in both and compilation in bytecode;
        they do not isolate dispatch. JSON captures parameters, command, host, raw samples, and summaries.
        """,
    )

    buggy_parser = _PARSER.replace(
        "                right = self._factor()\n",
        "                right = self._term()\n",
    )
    if buggy_parser == _PARSER or buggy_parser.count("right = self._term()") != 1:
        raise RuntimeError("debugging mutation did not apply exactly once")
    debug_root = "debugging/parser-associativity"
    for name, content in {
        "model.py": _MODEL,
        "lexer.py": _LEXER,
        "parser.py": buggy_parser,
        "semantics.py": _SEMANTICS,
        "compiler.py": _COMPILER,
        "vm.py": _VM,
        "api.py": _BYTECODE_API,
        "__init__.py": _INIT,
        "__main__.py": _MAIN,
    }.items():
        _write(workspace, f"{debug_root}/buggy/tinyvm/{name}", content)
    _write_implementation(workspace, f"{debug_root}/sealed/fixed", bytecode=True)
    _write(workspace, f"{debug_root}/regression.py", _DEBUG_REGRESSION)
    _write(workspace, f"{debug_root}/sealed/check_integrity.py", _DEBUG_INTEGRITY)
    _write(
        workspace,
        f"{debug_root}/README.md",
        """
        # Incident: a harmless parser cleanup changed subtraction

        Users report that chained subtraction produces a surprising value, while addition and simple
        two-operand subtraction still pass. Work only from `buggy`, this report, and `regression.py`.
        Explain the grammar invariant, minimize the failure, repair it, and add tests covering other
        operators at the same precedence. Reveal the sealed root cause only after your postmortem.
        """,
    )
    _write(
        workspace,
        f"{debug_root}/sealed/root-cause.md",
        """
        # Root cause

        The term parser consumed its right operand by recursively parsing another complete term.
        That changed `a-b-c` from `(a-b)-c` to `a-(b-c)`: right associativity hidden inside a small
        refactor. Parse one factor per loop iteration to preserve the grammar's left fold. The correct
        and buggy packages otherwise have identical parser text, as the integrity validator proves.
        """,
    )
    patch = "".join(
        unified_diff(
            buggy_parser.splitlines(keepends=True),
            _PARSER.splitlines(keepends=True),
            fromfile="a/debugging/parser-associativity/buggy/tinyvm/parser.py",
            tofile="b/debugging/parser-associativity/buggy/tinyvm/parser.py",
        )
    )
    _write(workspace, f"{debug_root}/sealed/patch.diff", patch)
    _write(
        workspace,
        f"{debug_root}/sealed/investigation.md",
        """
        # Reproducible investigation

        `20 - 5` establishes basic subtraction; `20 - 5 - 3` distinguishes left and right grouping.
        Inspecting the AST shows a `Binary(20, '-', Binary(5, '-', 3))`. Comparing precedence loops
        isolates one operand-parser call. The regression passes against `sealed/fixed` and fails with
        exit 1 against `buggy`; the patch changes only that call.
        """,
    )

    review_root = "review_exercises/constant-folding"
    _write(workspace, f"{review_root}/proposed/optimizer.py", _PROPOSED_OPTIMIZER)
    _write(
        workspace,
        f"{review_root}/README.md",
        """
        # PR review: fold constant expressions before bytecode emission

        Review `proposed/optimizer.py` as a production change. Submit comments with severity, an
        observable counterexample, and a repair direction. Consider guest-language semantics,
        diagnostics/source locations, compile-time resource use, pass placement, and tests. Do not
        assume an optimization is valid merely because both operands are syntactically constant.
        """,
    )
    _write(workspace, f"{review_root}/sealed/demonstrate.py", _REVIEW_DEMONSTRATION)
    _write(
        workspace,
        f"{review_root}/sealed/EXPECTED_REVIEW.md",
        """
        # Expected review

        **Blocker:** the pass recursively folds both operands before handling `&&` or `||`. It raises
        division-by-zero for `false && (1/0)` although the language guarantees the RHS is unreachable.
        Fold the left side first and fold the RHS only when source semantics would evaluate it.

        **Major:** reconstructed AST nodes discard source provenance once locations are added, making
        optimized-program diagnostics unstable. Define a location-preservation rule before landing.

        **Major/design:** running guest arithmetic during compilation needs an explicit typed-error and
        resource policy; it must not leak arbitrary host exceptions or permit unbounded compile work.
        Add differential tests for every operator, overflow, errors, and short-circuit counterexamples.
        """,
    )


def generate_bytecode_slice(
    workspace: Path, payload: dict[str, Any], db: Database
) -> SliceResult:
    """Generate a deterministic, independently validated language/VM challenge pack."""

    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("bytecode slice workspace must be an existing real directory")
    entries = list(workspace.iterdir())
    marker = workspace / ".factory-workspace"
    if marker.exists() and (not marker.is_file() or marker.is_symlink()):
        raise ValueError("bytecode slice workspace marker must be a regular file")
    if any(entry.name != ".factory-workspace" for entry in entries):
        raise ValueError("bytecode slice workspace must be empty")
    requested_project = payload.get("project_id")
    if requested_project is not None and requested_project != PROJECT_ID:
        raise ValueError(f"bytecode slice project_id must be {PROJECT_ID}")
    provenance = _provenance(db, payload)
    _documents(workspace, provenance)
    _write_json(workspace, "PROVENANCE.json", provenance)

    _write_implementation(workspace, "sealed/reference", bytecode=True)
    _write_implementation(workspace, "alternatives/treewalk", bytecode=False)
    for name, content in {
        "model.py": _STARTER_MODEL,
        "lexer.py": _STARTER_LEXER,
        "parser.py": _STARTER_PARSER,
        "compiler.py": _STARTER_COMPILER,
        "vm.py": _STARTER_VM,
        "api.py": _STARTER_API,
        "__init__.py": _INIT,
    }.items():
        _write(workspace, f"starter/tinyvm/{name}", content)
    _write(
        workspace,
        "starter/README.md",
        """
        # Learner implementation

        Preserve the public exports in `tinyvm`. Add your own AST, lexer, parser, compiler, and VM
        modules incrementally. The scaffold intentionally raises `NotImplementedError`; passing a
        syntax/import check is not evidence that the language contract is complete.
        """,
    )
    _write_supporting_artifacts(workspace)

    catalog = {
        "id": "sprig-bytecode-vm",
        "name": "Sprig Language, Compiler, and Bytecode VM",
        "family": "languages-compilers",
        "type": "build-your-own-x-challenge-pack",
        "languages": ["Python 3.11"],
        "concepts": [
            "lexing", "recursive-descent parsing", "ASTs", "bytecode compilation",
            "stack virtual machines", "tree-walk interpreters", "resource bounds",
            "differential testing", "compiler debugging",
        ],
        "difficulty": 8,
        "estimated_human_hours": 18,
        "production_relevance": 8,
        "cs_depth": 9,
        "debugging_value": 9,
        "architecture_value": 9,
        "prerequisites": ["Python", "recursion", "basic language grammars"],
        "next": ["closures and lexical scope", "bytecode verification", "garbage collection", "debugger protocol"],
        "artifact_paths": {
            "starter": "starter",
            "public_tests": "public_tests",
            "reference": "sealed/reference",
            "treewalk_alternative": "alternatives/treewalk",
            "hidden_tests": "sealed/reference_tests",
            "fuzzer": "adversarial/grammar_fuzz.py",
            "benchmark": "benchmarks/benchmark.py",
            "debugging_challenge": "debugging/parser-associativity",
            "review_exercise": "review_exercises/constant-folding",
        },
        "validation_status": "GENERATED_CANDIDATE",
        "validation_targets": ["BUILDS", "TESTED", "FUZZED", "BENCHMARKED", "REVIEWED", "PARTIAL"],
        "deployment_status": "NOT_PRODUCTION_READY",
        "productionized": False,
        "provenance": provenance,
    }
    _write_json(workspace, "CATALOG.json", catalog)
    _write_json(
        workspace,
        "MANIFEST.yaml",
        {
            "schema_version": 1,
            "id": catalog["id"],
            "status": "GENERATED_CANDIDATE",
            "deployment_status": "NOT_PRODUCTION_READY",
            "productionized": False,
            "architectures": [
                {"name": "bytecode", "path": "sealed/reference", "role": "reference compiler and stack VM"},
                {"name": "treewalk", "path": "alternatives/treewalk", "role": "independent AST evaluator"},
            ],
            "shared_contract": "tinyvm.parse_source and tinyvm.run_source",
            "provenance_project_id": PROJECT_ID,
            "validation_targets": catalog["validation_targets"],
        },
    )

    required_paths = [
        "README.md", "REQUIREMENTS.md", "GRAMMAR.md", "BYTECODE.md", "CONCEPTS.md",
        "DESIGN_QUESTIONS.md", "TRADEOFFS.md", "PRODUCTION_GAPS.md", "PROVENANCE.json",
        "MANIFEST.yaml", "CATALOG.json", "starter/tinyvm/api.py", "public_tests/test_public.py",
        "sealed/reference/tinyvm/compiler.py", "sealed/reference/tinyvm/vm.py",
        "alternatives/treewalk/tinyvm/interpreter.py", "sealed/reference_tests/test_hidden.py",
        "adversarial/grammar_fuzz.py", "benchmarks/benchmark.py",
        "debugging/parser-associativity/buggy/tinyvm/parser.py",
        "debugging/parser-associativity/sealed/patch.diff",
        "review_exercises/constant-folding/proposed/optimizer.py",
        "review_exercises/constant-folding/sealed/EXPECTED_REVIEW.md",
    ]
    validators: list[dict[str, Any]] = [
        {"type": "required_paths", "name": "challenge-pack-structure", "paths": required_paths},
        {
            "type": "json_fields", "name": "manifest-contract", "path": "MANIFEST.yaml",
            "required": ["schema_version", "id", "status", "deployment_status", "productionized", "architectures", "provenance_project_id", "validation_targets"],
        },
        {
            "type": "json_fields", "name": "catalog-contract", "path": "CATALOG.json",
            "required": ["id", "family", "languages", "concepts", "difficulty", "artifact_paths", "validation_status", "deployment_status", "provenance"],
        },
        {
            "type": "command", "name": "all-python-syntax", "argv": ["python3", "environment/check_python.py"],
            "timeout_seconds": 30, "claims": ["BUILDS", "PARTIAL"],
        },
        {
            "type": "command", "name": "progressive-disclosure-boundary", "argv": ["python3", "environment/check_boundaries.py"],
            "timeout_seconds": 20, "claims": ["TESTED", "PARTIAL"],
        },
        {
            "type": "command", "name": "starter-importable-incomplete", "argv": ["python3", "environment/check_starter.py"],
            "env": {"PYTHONPATH": "starter"}, "timeout_seconds": 20, "claims": ["BUILDS", "PARTIAL"],
        },
    ]
    implementations = {"bytecode": "sealed/reference", "treewalk": "alternatives/treewalk"}
    for name, path in implementations.items():
        validators.extend(
            [
                {
                    "type": "command", "name": f"{name}-public-contract",
                    "argv": ["python3", "-m", "unittest", "discover", "-s", "public_tests", "-v"],
                    "env": {"PYTHONPATH": path}, "timeout_seconds": 30, "claims": ["TESTED", "PARTIAL"],
                },
                {
                    "type": "command", "name": f"{name}-withheld-contract",
                    "argv": ["python3", "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"],
                    "env": {"PYTHONPATH": path}, "timeout_seconds": 30, "claims": ["TESTED", "PARTIAL"],
                },
            ]
        )
    validators.extend(
        [
            {
                "type": "command", "name": "bytecode-instruction-contract",
                "argv": ["python3", "-m", "unittest", "discover", "-s", "sealed/bytecode_tests", "-v"],
                "env": {"PYTHONPATH": "sealed/reference"}, "timeout_seconds": 30,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command", "name": "deterministic-differential-fuzz",
                "argv": ["python3", "adversarial/grammar_fuzz.py", "--seed", "7401", "--iterations", "120", "--output", "reports/fuzz-smoke.json"],
                "produces": ["reports/fuzz-smoke.json"], "timeout_seconds": 45,
                "claims": ["FUZZED", "TESTED", "PARTIAL"],
            },
            {
                "type": "json_fields", "name": "fuzz-evidence-fields", "path": "reports/fuzz-smoke.json",
                "required": ["schema_version", "seed", "iterations", "corpus_sha256", "engines", "properties", "coverage", "failures"],
            },
            {
                "type": "command", "name": "debugging-bug-reproduces",
                "argv": ["python3", "debugging/parser-associativity/regression.py"],
                "env": {"PYTHONPATH": "debugging/parser-associativity/buggy"}, "expected_exit": 1,
                "timeout_seconds": 20, "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command", "name": "debugging-fix-restores-contract",
                "argv": ["python3", "debugging/parser-associativity/regression.py"],
                "env": {"PYTHONPATH": "debugging/parser-associativity/sealed/fixed"},
                "timeout_seconds": 20, "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command", "name": "debugging-isolated-mutation-integrity",
                "argv": ["python3", "debugging/parser-associativity/sealed/check_integrity.py"],
                "timeout_seconds": 20, "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command", "name": "review-finding-reproduction",
                "argv": ["python3", "review_exercises/constant-folding/sealed/demonstrate.py"],
                "env": {"PYTHONPATH": "sealed/reference"}, "timeout_seconds": 20,
                "claims": ["TESTED", "REVIEWED", "PARTIAL"],
            },
            {
                "type": "command", "name": "measured-architecture-benchmark",
                "argv": ["python3", "benchmarks/benchmark.py", "--samples", "7", "--output", "benchmarks/results/smoke.json"],
                "produces": ["benchmarks/results/smoke.json"], "timeout_seconds": 45,
                "claims": ["BENCHMARKED", "PARTIAL"],
            },
            {
                "type": "json_fields", "name": "benchmark-evidence-fields", "path": "benchmarks/results/smoke.json",
                "required": ["schema_version", "hypothesis", "measurement_scope", "parameters", "environment", "command", "raw_results", "interpretation_boundary"],
            },
            {"type": "tree_checksum", "name": "bytecode-pack-tree-checksum"},
        ]
    )
    files = sorted(path for path in workspace.rglob("*") if path.is_file())
    metadata = {
        "name": catalog["name"],
        "family": catalog["family"],
        "project_id": PROJECT_ID,
        "architecture_count": 2,
        "deployment_status": "NOT_PRODUCTION_READY",
        "productionized": False,
        "validation_targets": catalog["validation_targets"],
        "provenance": provenance,
    }
    evidence = {
        "handler": "generate_bytecode_slice",
        "project_id": PROJECT_ID,
        "external_validation_required": True,
        "validator_count": len(validators),
        "generated_file_count": len(files),
        "generated_bytes": sum(path.stat().st_size for path in files),
        "candidate_tree_sha256": tree_sha256(workspace),
        "benchmark_generated_during_validation": True,
        "deployment_status": "NOT_PRODUCTION_READY",
    }
    return SliceResult(
        evidence=evidence,
        validators=validators,
        artifact_type="bytecode_vm_challenge_pack",
        semantic_path="projects/languages/sprig-bytecode-vm",
        metadata=metadata,
    )
