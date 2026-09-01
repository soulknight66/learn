# Adversarial stage

After ordinary tests pass, use `corpus/cases.json` as seeds for boundary and mutation tests. The cases
name an expected outcome category without prescribing implementation. For each seed, vary whitespace,
comments, nesting, repeated operators, identifier length, literal length, and configured limits.

Useful properties include: termination under a host timeout, a typed deterministic error, no console
or filesystem effects, no partial VM output after validation failure, no input mutation, and identical
tree/VM results for valid terminating sources.

This corpus was generated locally and was not fuzzed on the factory host.
