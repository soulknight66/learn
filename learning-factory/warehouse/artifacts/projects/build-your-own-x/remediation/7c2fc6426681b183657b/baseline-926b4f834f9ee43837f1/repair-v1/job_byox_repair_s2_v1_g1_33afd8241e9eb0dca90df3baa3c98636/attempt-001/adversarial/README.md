# Adversarial evaluation plan

Adversarial validation should generate inputs around every transition boundary, launch a fresh
process per case, enforce a timeout, and compare exit status plus both output streams. High-value
families include:

- 65,535/65,536/65,537 input bytes, final comments without newline, NUL separators, and `#` inside a
  token;
- signed-decimal endpoints, long zero prefixes, overflow on the last digit, and near-numeric names;
- 255/256/257 stack cells, return continuations, and dictionary entries;
- 63/64/65 nested patches, unmatched `else`/`then`, missing `;`, and duplicate names;
- code arenas ending exactly on an opcode, operand, or RET boundary;
- all division sign pairs, zero, the signed-overflow pair, and wrapping add/subtract/multiply;
- recursive definitions that stop at the boundary and ones that exceed it.

No fuzzing label is claimed: these are test-design notes, not evidence that a fuzzer was run.
