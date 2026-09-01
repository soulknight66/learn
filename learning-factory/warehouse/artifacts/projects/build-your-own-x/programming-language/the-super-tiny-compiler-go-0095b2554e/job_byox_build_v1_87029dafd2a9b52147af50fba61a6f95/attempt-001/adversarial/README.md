# Adversarial validation inventory

This evaluator-facing area describes hostile cases; executable versions are in `sealed/reference_tests/adversarial_test.go` and `fuzz_test.go`.

The matrix covers empty or duplicate EOF streams, invalid token kinds and payloads, non-monotonic spans, nil AST children, inconsistent analysis maps, negative and out-of-range slots, load-before-store, duplicate stores, stack underflow/residue, unknown opcodes, stray operands, invalid spans, early/missing halt, malformed UTF-8, numeric boundaries, partial-output rollback, input immutability, repeated runs, and concurrent runs.

Fuzz targets are present but were not run on the generation host because Go was unavailable. Their existence is not evidence of fuzz coverage or correctness.
