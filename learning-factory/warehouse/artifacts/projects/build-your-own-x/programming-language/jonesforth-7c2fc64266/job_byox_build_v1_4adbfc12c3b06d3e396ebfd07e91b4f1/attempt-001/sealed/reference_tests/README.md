# Sealed reference tests

These evaluator-only unittests exercise contract boundaries omitted from the public examples:
numeric extrema, all checked-overflow paths, exact input and stack limits, short-read accumulation,
compile atomicity, and runtime error timing.

Run from the repository root:

    python3 -m unittest discover -s sealed/reference_tests -v

The suite builds sealed/reference/ itself and does not alter the learner starter.

