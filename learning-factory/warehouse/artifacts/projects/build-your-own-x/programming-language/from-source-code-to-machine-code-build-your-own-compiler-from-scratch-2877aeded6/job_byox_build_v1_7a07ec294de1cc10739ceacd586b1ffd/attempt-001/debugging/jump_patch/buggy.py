def patch_jump(code, operand_index, destination_instruction_number):
    """Intentionally defective: `code` is already a bytearray."""
    code[operand_index:operand_index + 4] = destination_instruction_number.to_bytes(
        4, byteorder="little", signed=False
    )
