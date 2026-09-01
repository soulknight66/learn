# Adversarial corpus

The files in `cases/` are lowercase hexadecimal MNO1 inputs for verifier experiments. Decode with
`bytes.fromhex(Path(path).read_text())`; do not execute a case until the whole binary has been validated.

Expected categories:

- `invalid_magic.hex`: header rejection;
- `stack_underflow.hex`: structurally decoded instructions with invalid stack flow;
- `jump_into_operand.hex`: a numerically in-range target that is not an instruction boundary.

These cases are examples, not a complete hidden test set. In particular, add mutations for truncation,
declared-length disagreement, early HALT, unreachable code, merge-depth disagreement, slot bounds, and
large resource requests.
