"""Validated Minnow stack-machine execution."""

from .bytecode import validate


def run_bytecode(program, stdout, *, step_limit=1_000_000):
    if not isinstance(program, (bytes, bytearray)):
        raise TypeError("program must be bytes or bytearray")
    if isinstance(step_limit, bool) or not isinstance(step_limit, int):
        raise TypeError("step_limit must be an integer")
    if step_limit <= 0:
        raise ValueError("step_limit must be positive")
    verified = validate(bytes(program))
    # TODO: dispatch verified instructions with explicit signed-64 arithmetic.
    del verified, stdout
    raise NotImplementedError("implement virtual machine")
