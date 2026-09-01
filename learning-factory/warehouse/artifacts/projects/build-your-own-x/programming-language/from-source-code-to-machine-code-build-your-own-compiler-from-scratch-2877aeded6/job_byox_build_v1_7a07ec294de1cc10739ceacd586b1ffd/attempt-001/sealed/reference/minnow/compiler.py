"""Lexical resolution and bytecode emission for the reference compiler."""

import struct

from .bytecode import Opcode, encode
from .errors import SemanticError
from .model import Assign, Binary, Block, If, Let, Literal, Print, TokenKind, Unary, Variable, While


BINARY_OPCODES = {
    TokenKind.PLUS: Opcode.ADD,
    TokenKind.MINUS: Opcode.SUB,
    TokenKind.STAR: Opcode.MUL,
    TokenKind.SLASH: Opcode.DIV,
    TokenKind.PERCENT: Opcode.MOD,
    TokenKind.EQUAL_EQUAL: Opcode.EQ,
    TokenKind.BANG_EQUAL: Opcode.NE,
    TokenKind.LESS: Opcode.LT,
    TokenKind.LESS_EQUAL: Opcode.LE,
    TokenKind.GREATER: Opcode.GT,
    TokenKind.GREATER_EQUAL: Opcode.GE,
}

UNARY_OPCODES = {
    TokenKind.MINUS: Opcode.NEG,
    TokenKind.BANG: Opcode.NOT,
}


class Compiler:
    def __init__(self):
        self.code = bytearray()
        self.scopes = [{}]
        self.next_slot = 0

    def compile(self, program):
        for statement in program.statements:
            self._statement(statement)
        self._opcode(Opcode.HALT)
        return encode(self.next_slot, self.code)

    def _statement(self, statement):
        if isinstance(statement, Let):
            # Resolve before declaration so an outer binding is visible in a self-initializer.
            self._expression(statement.initializer)
            slot = self._declare(statement.name)
            self._slot_instruction(Opcode.STORE, slot)
        elif isinstance(statement, Assign):
            self._expression(statement.value)
            self._slot_instruction(Opcode.STORE, self._lookup(statement.name))
        elif isinstance(statement, Print):
            self._expression(statement.value)
            self._opcode(Opcode.PRINT)
        elif isinstance(statement, Block):
            self._block(statement)
        elif isinstance(statement, If):
            self._expression(statement.condition)
            false_patch = self._forward_jump(Opcode.JUMP_IF_FALSE)
            self._block(statement.then_branch)
            if statement.else_branch is None:
                self._patch(false_patch, len(self.code))
            else:
                end_patch = self._forward_jump(Opcode.JUMP)
                self._patch(false_patch, len(self.code))
                self._block(statement.else_branch)
                self._patch(end_patch, len(self.code))
        elif isinstance(statement, While):
            condition_address = len(self.code)
            self._expression(statement.condition)
            exit_patch = self._forward_jump(Opcode.JUMP_IF_FALSE)
            self._block(statement.body)
            self._opcode(Opcode.JUMP)
            self.code.extend(struct.pack(">I", condition_address))
            self._patch(exit_patch, len(self.code))
        else:
            raise TypeError(f"unsupported statement node {type(statement).__name__}")

    def _block(self, block):
        self.scopes.append({})
        try:
            for statement in block.statements:
                self._statement(statement)
        finally:
            self.scopes.pop()

    def _expression(self, expression):
        if isinstance(expression, Literal):
            self._opcode(Opcode.CONST)
            self.code.extend(struct.pack(">q", expression.value))
        elif isinstance(expression, Variable):
            self._slot_instruction(Opcode.LOAD, self._lookup(expression.name))
        elif isinstance(expression, Unary):
            self._expression(expression.right)
            self._opcode(UNARY_OPCODES[expression.operator.kind])
        elif isinstance(expression, Binary):
            self._expression(expression.left)
            self._expression(expression.right)
            self._opcode(BINARY_OPCODES[expression.operator.kind])
        else:
            raise TypeError(f"unsupported expression node {type(expression).__name__}")

    def _declare(self, token):
        current = self.scopes[-1]
        if token.lexeme in current:
            raise SemanticError(
                f"duplicate declaration of {token.lexeme!r}",
                line=token.line,
                column=token.column,
                code="SEM002",
            )
        if self.next_slot >= 65535:
            raise SemanticError("program needs more than 65,535 local slots", line=token.line, column=token.column, code="SEM003")
        slot = self.next_slot
        self.next_slot += 1
        current[token.lexeme] = slot
        return slot

    def _lookup(self, token):
        for scope in reversed(self.scopes):
            if token.lexeme in scope:
                return scope[token.lexeme]
        raise SemanticError(
            f"undefined name {token.lexeme!r}",
            line=token.line,
            column=token.column,
            code="SEM001",
        )

    def _opcode(self, opcode):
        self.code.append(int(opcode))

    def _slot_instruction(self, opcode, slot):
        self._opcode(opcode)
        self.code.extend(struct.pack(">H", slot))

    def _forward_jump(self, opcode):
        self._opcode(opcode)
        operand_position = len(self.code)
        self.code.extend(b"\x00\x00\x00\x00")
        return operand_position

    def _patch(self, operand_position, destination):
        self.code[operand_position:operand_position + 4] = struct.pack(">I", destination)


def compile_program(program):
    return Compiler().compile(program)
