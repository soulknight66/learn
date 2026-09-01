# Exercise: a branch into nowhere

The emitter in `buggy.py` stores instruction records and later serializes them to variable-width bytes.
Its patched destination is rejected as "not an instruction boundary" once constants precede a branch.

Explain both representation errors, construct the smallest failing instruction sequence, and decide
whether labels should resolve before or during serialization.
