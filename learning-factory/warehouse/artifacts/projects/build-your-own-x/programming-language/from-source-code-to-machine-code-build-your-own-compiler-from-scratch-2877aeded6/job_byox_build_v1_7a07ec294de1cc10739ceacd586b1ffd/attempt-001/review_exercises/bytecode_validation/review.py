def run(decoded, stdout):
    stack = []
    for instruction in decoded:
        if instruction.opcode == "CONST":
            stack.append(instruction.operand)
        elif instruction.opcode == "PRINT":
            if not stack:
                raise ValueError("underflow")
            stdout.write(f"{stack.pop()}\n")
        elif instruction.opcode == "HALT":
            return
        else:
            raise ValueError("unknown opcode")
