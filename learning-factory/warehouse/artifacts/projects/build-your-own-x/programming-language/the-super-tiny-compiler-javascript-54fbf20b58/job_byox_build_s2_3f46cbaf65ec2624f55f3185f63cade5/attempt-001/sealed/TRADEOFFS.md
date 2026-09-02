# Trade-offs

## A compact language instead of a JavaScript subset

Ripple has two statement forms, primitive expressions, and a closed built-in set. This keeps the entire pipeline observable in one exercise and removes host-global lookup. The cost is that control flow, mutation, functions, and objects are unavailable, so the project teaches mechanisms rather than a general-purpose language.

## Recursive descent

One parser function per precedence tier mirrors the grammar and yields focused diagnostics. A Pratt parser would make adding operators more table-driven, but introduces binding-power machinery before the learner has seen the basic phase boundaries. Deeply nested input can exhaust the JavaScript stack; an untrusted-input implementation needs explicit depth accounting or an iterative parser.

## Dynamic primitive semantics

Arithmetic follows JavaScript primitive operations, including string addition, `NaN`, infinity, and operand-valued logical operators. That makes lowering small and enables differential checking. It also inherits surprising coercions. A typed language would move many failures into analysis at the cost of a type representation and inference/checking rules.

## WeakMap resolution side tables

Semantic binding data lives in `WeakMap`s keyed by AST identity. The syntax tree stays serializable and free of backend annotations. The consequence is that any tree rewrite needs fresh analysis before generation. The pipeline makes that transition explicit.

## Pure optimizer

Rebuilding the whole tree uses more allocation than in-place edits, but callers can retain and compare the parsed and optimized trees safely. Only literal unary and binary folds are performed. This leaves performance on the table but reduces the proof surface around exceptions and evaluation order.

## JavaScript function-body output

A body makes generated code easy to exercise with `Function` in a trusted test harness. It is not a safe deployment container: compiling untrusted input does not make execution trustworthy. The tree interpreter avoids dynamic evaluation, while production execution would still require a separate process and OS sandbox.
