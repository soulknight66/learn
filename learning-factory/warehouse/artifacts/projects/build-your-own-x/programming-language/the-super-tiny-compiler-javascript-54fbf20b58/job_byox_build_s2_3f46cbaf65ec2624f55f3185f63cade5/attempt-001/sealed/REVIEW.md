# Reference implementation review

## Summary

The implementation is suitable as an educational oracle, not as a production compiler service. Its strongest properties are closed-world name lowering, phase-specific diagnostics, a non-evaluating interpreter, pure AST optimization, no external dependencies, and tests that compare three execution paths.

## Correctness findings

- The scanner's outer loop either advances, enters a loop that advances, or throws. EOF is appended exactly once.
- Binary precedence and left associativity follow directly from parser delegation and loops. Unary operators recurse.
- Initializers are analyzed before declarations enter scope. Duplicate, reserved, unknown, non-callable, unknown-built-in, and arity errors have separate codes.
- Generated bindings come only from integer semantic IDs. Built-in targets come only from a frozen mapping. Strings use JSON encoding with explicit U+2028/U+2029 escaping.
- Logical operators are handled separately in the interpreter, preserving short-circuiting and operand results.
- The optimizer refuses to create non-finite literals and the generator preserves negative zero.

## Remaining risks

- Recursive scanning is avoided, but recursive parsing, analysis, optimization, interpretation, and generation can overflow on adversarial nesting.
- Compilation has no timeout or memory enforcement. The partial limit wrapper checks sizes after some phases and cannot substitute for process isolation.
- JavaScript number/coercion behavior may be unintuitive and is not portable to a backend with different numeric semantics.
- Token and AST inputs accepted directly by `parse`, `analyze`, and later phases are trusted internal structures; malformed handcrafted structures generally receive `TypeError`, not polished diagnostics.
- Generated code is intended for a trusted harness. Running it in the main process grants it that process's CPU and memory even though source-controlled names are constrained.
- No Node runtime was available on the generation host, so the JavaScript syntax and behavior suites remain independently unexecuted here.

## Recommendation

Use the oracle for learning validation after running the sealed suites on Node.js 18+. Do not mark the artifact productionized. Before service deployment, add iterative/depth-limited phases, subprocess isolation, strict budgets, cancellation, structured logging, versioned output, and independent security review.
