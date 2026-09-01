def execute_jump_if_false(instruction, stack, instruction_pointer, instructions):
    target = instruction[1]
    if not stack[-1]:
        instruction_pointer = target
    return instruction_pointer
