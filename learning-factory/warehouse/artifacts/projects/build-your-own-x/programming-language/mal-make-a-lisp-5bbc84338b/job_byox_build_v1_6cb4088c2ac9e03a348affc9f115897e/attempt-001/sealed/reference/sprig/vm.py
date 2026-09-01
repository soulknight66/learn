"""Checked stack virtual machine for Sprig bytecode."""

from .compiler import Bytecode
from .errors import LanguageError
from .runtime import Builtin, Environment, default_environment, is_truthy


class VirtualMachine(object):
    def __init__(self, max_steps=10000):
        if type(max_steps) is not int or max_steps < 0:
            raise ValueError("max_steps must be a non-negative integer")
        self.max_steps = max_steps

    @staticmethod
    def _malformed(message):
        raise LanguageError("VM_MALFORMED", message)

    @staticmethod
    def _one_operand(instruction, operation):
        if len(instruction) != 2:
            VirtualMachine._malformed("{0} requires one operand".format(operation))
        return instruction[1]

    def run(self, bytecode, env=None):
        if not isinstance(bytecode, Bytecode):
            raise LanguageError("VM_BYTECODE", "expected a Bytecode object")
        if env is None:
            env = default_environment()
        if not isinstance(env, Environment):
            raise LanguageError("VM_ENV", "expected an Environment")
        instructions = bytecode.instructions
        constants = bytecode.constants
        if not isinstance(instructions, list) or not isinstance(constants, list):
            self._malformed("bytecode fields must be lists")

        stack = []
        instruction_pointer = 0
        steps = 0
        while instruction_pointer < len(instructions):
            steps += 1
            if steps > self.max_steps:
                raise LanguageError("VM_STEP_LIMIT", "VM step limit exceeded")
            instruction = instructions[instruction_pointer]
            if not isinstance(instruction, tuple) or not instruction or not isinstance(instruction[0], str):
                self._malformed("instruction must be a non-empty tuple beginning with text")
            operation = instruction[0]
            instruction_pointer += 1

            if operation == "CONST":
                index = self._one_operand(instruction, operation)
                if type(index) is not int or index < 0 or index >= len(constants):
                    self._malformed("constant index is out of range")
                stack.append(constants[index])
                continue

            if operation == "LOAD":
                name = self._one_operand(instruction, operation)
                if not isinstance(name, str):
                    self._malformed("LOAD name must be text")
                stack.append(env.get(name))
                continue

            if operation == "POP":
                if len(instruction) != 1 or not stack:
                    self._malformed("POP requires one stack value and no operands")
                stack.pop()
                continue

            if operation in ("JUMP", "JUMP_IF_FALSE"):
                target = self._one_operand(instruction, operation)
                if type(target) is not int or target < 0 or target >= len(instructions):
                    self._malformed("jump target is out of range")
                if operation == "JUMP":
                    instruction_pointer = target
                else:
                    if not stack:
                        self._malformed("JUMP_IF_FALSE requires one stack value")
                    condition = stack.pop()
                    if not is_truthy(condition):
                        instruction_pointer = target
                continue

            if operation == "CALL":
                count = self._one_operand(instruction, operation)
                if type(count) is not int or count < 0:
                    self._malformed("CALL count must be a non-negative integer")
                if len(stack) < count + 1:
                    self._malformed("CALL stack underflow")
                procedure_index = len(stack) - count - 1
                procedure = stack[procedure_index]
                arguments = stack[procedure_index + 1:]
                del stack[procedure_index:]
                if not isinstance(procedure, Builtin):
                    raise LanguageError("VM_NOT_CALLABLE", "compiled calls require a builtin")
                stack.append(procedure.invoke(arguments))
                continue

            if operation == "RETURN":
                if len(instruction) != 1:
                    self._malformed("RETURN takes no operands")
                if len(stack) != 1:
                    self._malformed("RETURN requires exactly one stack value")
                return stack[0]

            self._malformed("unknown operation: {0}".format(operation))

        raise LanguageError("VM_NO_RETURN", "program ended without RETURN")
