# Sealed implementation review

## Disposition

The reference is a credible educational implementation, but this artifact remains `GENERATED` and
`PARTIAL`. It has not been executed on a JavaScript runtime in the generation environment and this
authoring review is not an independent `REVIEWED`, `TESTED`, or production-readiness label.

## Scope reviewed

The static review traced tokenization, each grammar production, AST evaluation, bytecode lowering,
jump destinations, VM dispatch, error inheritance/codes, work budgets, and the public/staged test
contracts. It also compared the starter, public tests, sealed tests, adversarial runner, and benchmark
harness against `REQUIREMENTS.md`.

## Positive properties visible in the code

- The scanner makes progress on every successful branch, preserves exact lexemes, recognizes
  longest operators, and reports one-based locations.
- Precedence and associativity are expressed directly in separate parser levels. Optional `else`
  becomes an explicit `null` AST field.
- Both engines use `Map` for program bindings and share type/operator helpers, while retaining
  independent control-flow mechanisms suitable for parity testing.
- Arithmetic results are checked before they can introduce `NaN` or infinities into the Pebble
  value domain, with a stable `NON_FINITE_NUMBER` error category.
- Compilation creates fresh deterministic arrays, uses a constants pool, and patches absolute jump
  destinations without mutating the AST.
- The VM checks the exact bytecode envelope and instruction fields, pool/name/target operands,
  terminal `HALT`, stack underflow, final stack height, and configured work budget. It does not use
  dynamic code evaluation.
- Dedicated syntax, runtime, bytecode, and step-limit error relationships support stable caller
  checks without requiring exact message text.
- Evaluator-stage runners use a fixed candidate/oracle binding, reject candidate module escapes,
  and report both path-and-content identities. A default-deny policy constructs cumulative learner
  views in memory and checks that sealed and unrevealed paths are absent.

## Residual risks and follow-up

1. **Execution evidence is missing (blocking for validation labels).** Run the public, reference, and
   adversarial suites on a supported Node.js version. A static trace cannot detect every syntax,
   module-loading, or runtime defect.
2. **The parser and evaluator use host recursion.** Deep grouping or unary chains can exhaust the
   JavaScript call stack before a Pebble work limit applies. Add source-size and nesting limits or
   use iterative parsing/evaluation for hostile input.
3. **Memory is not bounded.** Source, tokens, AST, constants, instructions, variables, output, and VM
   stack can grow independently of a wall-clock or heap limit. Production use needs an isolated
   process plus explicit size/output limits.
4. **Stack validation is partly dynamic.** Structural bytecode validation runs before dispatch, but
   control-flow-aware stack-height analysis is deferred to runtime underflow/final-height checks.
   A verifier should reject inconsistent merge heights and stack-growing cycles before execution.
5. **Projection and evaluator controls still need independent execution.** The view audit and fixed
   module binding are deterministic code, but this authoring review is not transfer or isolation
   evidence. Run them in the actual harness and inspect exported stage views before learner use.
6. **Runtime diagnostics lack source spans.** Syntax diagnostics carry locations, while runtime and
   compiled errors generally do not. Source maps or span metadata would materially improve tooling.

The sealed production assessment lists broader operational gates. None of these recommendations is
claimed as implemented.
