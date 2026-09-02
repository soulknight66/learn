# Starter milestones

Implement `compiler.js` without changing its exports.

1. **Scanner:** emit located tokens and make every input-loop branch consume or throw.
2. **Parser:** build literals and grouping, then unary, binary precedence levels, calls, and statements.
3. **Analyzer:** process statements in order, assign safe binding identities, and validate built-ins.
4. **Interpreter:** evaluate the analyzed tree with a closed built-in table.
5. **Generator:** emit a strict JavaScript function body using safe internal names.
6. **Optimizer:** make pure, behavior-preserving constant folds and compare optimized/unoptimized results.
7. **Integration:** return all phase artifacts from `pipeline` and stabilize diagnostics.

Run the public suite from the repository root:

```text
node --test public_tests/compiler.test.js
```

Do not install packages; the exercise is intentionally dependency-free.
