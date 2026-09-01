"""Compiler for Sprig's deliberately bounded expression subset."""

from .errors import LanguageError
from .printer import print_value
from .values import Symbol


_UNSUPPORTED = frozenset(("def", "set!", "let", "fn", "and", "or"))


class Bytecode(object):
    __slots__ = ("instructions", "constants")

    def __init__(self, instructions, constants):
        self.instructions = list(instructions)
        self.constants = list(constants)

    def disassemble(self):
        lines = []
        for index, instruction in enumerate(self.instructions):
            if not isinstance(instruction, tuple) or not instruction:
                rendered = "<malformed>"
            else:
                operation = str(instruction[0])
                operands = " ".join(str(item) for item in instruction[1:])
                rendered = operation + ((" " + operands) if operands else "")
                if operation == "CONST" and len(instruction) == 2:
                    constant_index = instruction[1]
                    if type(constant_index) is int and 0 <= constant_index < len(self.constants):
                        try:
                            rendered += " ; " + print_value(self.constants[constant_index])
                        except LanguageError:
                            rendered += " ; <unprintable>"
            lines.append("{0:04d} {1}".format(index, rendered))
        return "\n".join(lines)


class Compiler(object):
    def __init__(self):
        self._instructions = []
        self._constants = []

    def compile(self, form):
        self._instructions = []
        self._constants = []
        try:
            self._compile_form(form)
        except RecursionError:
            raise LanguageError("COMPILE_DEPTH", "compiler nesting limit exceeded")
        self._emit("RETURN")
        return Bytecode(self._instructions, self._constants)

    def _emit(self, operation, *operands):
        index = len(self._instructions)
        self._instructions.append(tuple([operation] + list(operands)))
        return index

    def _constant(self, value):
        index = len(self._constants)
        self._constants.append(value)
        self._emit("CONST", index)

    def _patch(self, index, target):
        operation = self._instructions[index][0]
        self._instructions[index] = (operation, target)

    def _compile_form(self, form):
        if isinstance(form, Symbol):
            self._emit("LOAD", form.name)
            return
        if not isinstance(form, list):
            self._constant(form)
            return
        if not form:
            self._constant([])
            return

        head = form[0]
        special = head.name if isinstance(head, Symbol) else None
        if special in _UNSUPPORTED:
            raise LanguageError(
                "COMPILE_UNSUPPORTED", "special form is outside compiler subset: {0}".format(special)
            )
        if special == "quote":
            if len(form) != 2:
                raise LanguageError("COMPILE_FORM", "quote expects one form")
            self._constant(form[1])
            return
        if special == "if":
            if len(form) not in (3, 4):
                raise LanguageError("COMPILE_FORM", "if expects two or three operands")
            self._compile_form(form[1])
            false_jump = self._emit("JUMP_IF_FALSE", -1)
            self._compile_form(form[2])
            end_jump = self._emit("JUMP", -1)
            self._patch(false_jump, len(self._instructions))
            if len(form) == 4:
                self._compile_form(form[3])
            else:
                self._constant(None)
            self._patch(end_jump, len(self._instructions))
            return
        if special == "do":
            if len(form) == 1:
                self._constant(None)
                return
            for child in form[1:-1]:
                self._compile_form(child)
                self._emit("POP")
            self._compile_form(form[-1])
            return

        self._compile_form(head)
        for child in form[1:]:
            self._compile_form(child)
        self._emit("CALL", len(form) - 1)
