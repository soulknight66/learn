# Code-review exercises

These prompts are evaluator material. Each answer is kept separately under `sealed/review_exercises/`.

## Error-contract review

Review a proposed `Build` that catches every stage error and returns `fmt.Errorf("build failed: %v", err)`. Assess compatibility with callers using `errors.As`, error-stage precedence, and deterministic diagnostics. Recommend a minimal correction.

## Bytecode-validation review

Review a proposed validator that converts `instruction.Operand` to `int`, indexes `initialized[slot]`, and only afterward checks `slot < SlotCount`. Identify portability and safety failures, including negative operands, and state the correct ordering of checks.
