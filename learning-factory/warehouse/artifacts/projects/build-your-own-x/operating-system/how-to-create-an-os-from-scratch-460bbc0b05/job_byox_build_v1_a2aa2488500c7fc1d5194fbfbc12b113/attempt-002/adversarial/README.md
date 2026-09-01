# Adversarial validation notes

This directory records black-box test themes for an independent validator. It contains no expected
outputs or reference implementation details.

- Exhaust every fixed-capacity table, then verify the preceding objects remain usable.
- Exercise every API with null output pointers and boundary indices.
- Reuse scheduler slots after reaping and filesystem slots after unlinking.
- Verify rejected virtual-memory and filesystem writes leave earlier bytes unchanged.
- Drive long state-machine sequences and check the public invariants after every step.

Concrete adversarial cases and their implementation belong under `sealed/reference_tests/`.
