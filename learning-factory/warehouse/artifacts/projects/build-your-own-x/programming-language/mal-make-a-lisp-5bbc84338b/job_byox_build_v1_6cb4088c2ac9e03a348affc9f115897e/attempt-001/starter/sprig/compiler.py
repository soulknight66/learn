"""Bytecode representation and compiler (milestone 4)."""


class Bytecode(object):
    def __init__(self, instructions, constants):
        self.instructions = instructions
        self.constants = constants

    def disassemble(self):
        raise NotImplementedError("milestone 4: Bytecode.disassemble")


class Compiler(object):
    def compile(self, form):
        raise NotImplementedError("milestone 4: Compiler.compile")
