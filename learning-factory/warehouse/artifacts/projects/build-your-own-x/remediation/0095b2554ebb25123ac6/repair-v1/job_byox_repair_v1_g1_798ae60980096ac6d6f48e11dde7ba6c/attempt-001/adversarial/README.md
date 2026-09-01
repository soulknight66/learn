# Adversarial validation inventory

This evaluator-facing area describes hostile cases. Oracle self-tests are in `sealed/reference_tests/`; candidate-targeted acceptance tests are in `sealed/learner_tests/contract_test.go` and are run only through the sealed harness.

The executable inventory is traceable to named tests:

- `TestForgedTokenStreamsAreRejected` covers empty/missing/duplicate EOF, keyword payload mismatch, unknown kinds, backward spans, and the impossible column-after-newline coordinate.
- `TestCallerConstructedASTAndAnalysisAreRejected` covers nil AST children, cycles/shared nodes, and inconsistent analysis maps.
- `TestAdversarialBytecodeTable` directly names negative and out-of-range slot operands, load-before-store, duplicate store, stack underflow/residue, unknown opcode, stray operand, reversed/zero spans, and early/missing halt.
- `TestArithmeticBoundariesAndTransactionalOutput`, `TestNegativeAndOutOfRangeSlotsAreRejected`, `TestImpossibleLineChangingTokenGapIsRejected`, and `TestConcurrentRunUsesFreshStateAndPreservesInput` apply the highest-risk cases to the learner module selected by the harness.
- `TestScanRejectsBadByteAndLargeInteger`, `TestCheckedArithmetic`, `TestFailureDoesNotExposePartialOutput`, `TestValidatorAndRunDoNotMutateInput`, and `TestConcurrentRunsHaveFreshState` cover malformed bytes, numeric boundaries, rollback, immutability, repeatability, and concurrency in public or oracle layers.

`FuzzValidateNeverPanicsOrMutates` uses independent opcode, operand, span, and slot-count inputs and starts from structurally valid streams as well as an invalid negative-slot seed. Fuzz targets were not run on the repair host because Go was unavailable. Their existence is not evidence of fuzz coverage or correctness.
