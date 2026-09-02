# Learner implementation guide

Work only in `starter/` for the exercise. Do not inspect or modify `sealed/`,
`adversarial/`, `debugging/`, `review_exercises/`, or `benchmarks/`; those paths
belong to independent evaluation.

Preserve the command-line and language contracts in `REQUIREMENTS.md`. Build
with `make -C starter` and run the public smoke tests with:

```bash
python3 public_tests/run_tests.py
```

Useful implementation order:

1. lexer with locations and checked integer conversion;
2. precedence parser and owned AST;
3. declaration/use validation;
4. bounded tree-walking evaluator;
5. x86-64 code generation and differential tests.

Use argv arrays rather than shell command strings in any test driver. Put
temporary build output in a temporary directory. Do not weaken diagnostics or
execution limits just to satisfy a test.
