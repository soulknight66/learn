# Independent review

## Advisory verdict: PASS

No material correctness, educational, provenance-boundary, or validation-honesty defect was found in the submitted challenge pack. The oracle survived static inspection and every environment-permitted independent check. This verdict is advisory: it does not publish `REVIEWED`, and it does not replace an acceptance run on Node.js 18+.

## Prioritized findings

### 1. Acceptance gate: run the target Node suites

Node.js and npm are absent from this review environment. Consequently, neither the learner-facing `node:test` suite nor the sealed Node suites and CLI were executed here. GJS parsed all 19 JavaScript files, the submitted smoke suite passed 35 assertions, and reviewer-authored GJS checks passed 1,824 assertions/outcomes across semantic, limit, bytecode, and adversarial cases. That is strong cross-engine evidence, but it does not establish Node-specific build or test status.

Before promotion, an orchestrator-controlled validator should run:

```text
node --version
node --check sealed/reference/compiler.js
node --test public_tests/compiler.test.js
node --test sealed/reference_tests/compiler.test.js sealed/reference_tests/bytecode.test.js sealed/reference_tests/production.test.js
node --test sealed/adversarial/compiler.adversarial.test.js
```

The starter's behavioral failures are expected until a learner implements it; acceptance of the pack should validate the sealed oracle independently and confirm that public failures are clean TODO failures rather than harness failures.

### 2. Isolation gate: enforce progressive disclosure in the harness

The material is organized well: learner documents point from requirements to concepts, milestones, public tests, and design questions, while reference code, answer keys, adversarial tests, benchmarks, and production material live below `sealed` path segments. However, all of those files are readable in this reviewer copy. `AGENTS.md` is guidance, not access control.

The student-view publisher must recursively exclude every sealed path segment, including the nested debugging and code-review answers, as well as provenance and validation records where policy requires. This review could inspect organization but not the external view-construction policy, so transfer/isolation remains unverified.

### 3. Provenance is internally consistent; external derivation remains unavailable

Strict parsing found no duplicate JSON keys. The manifest snapshot identifier matches `PROVENANCE.json`, the canonical provenance hash is stable, and the boundary consistently describes the catalog as CC0-1.0 while treating the linked project as `NOASSERTION` and provenance-only. Only one HTTP(S) URL occurs, in that upstream-reference field, and no common credential signature was found.

The immutable catalog baseline and upstream content were not available, so this review cannot independently re-derive the recorded commit/content/license hashes or prove the no-copy assertion. That is a review limitation, not evidence of a boundary violation.

### 4. Validation claims are appropriately narrow

The manifest remains `GENERATED` + `PARTIAL`, requires independent validation, and explicitly sets `productionized: false`. The supplied record clearly says Node tests, fuzzing, benchmarking, deployment, and production validation were not performed. The benchmark driver records no invented timing, and the production note accurately calls its size-limit wrapper incomplete. No claim inflation was found.

## Correctness and security evidence

- The scanner advances or throws, emits UTF-16 offsets and located EOF, and handles comments, escapes, CRLF, malformed strings, numbers, and operators consistently with the written grammar.
- The recursive-descent parser implements every precedence tier and left associativity; semantic analysis applies initializer-before-binding scope, stable binding IDs, builtin collision checks, bare-builtin call rules, and arity checks.
- The optimizer rebuilds the AST, preserves negative zero, avoids non-finite literals, and does not fold calls or otherwise force skipped logical branches.
- Generation starts in strict mode, emits only opaque integer-derived binding names, selects callees from a closed table, encodes string data, and parenthesizes expressions. Interpretation is a separate tree walk without `eval`, `Function`, `vm`, or generated-code execution.
- A reviewer-authored matrix compared interpreter output with optimized and unoptimized generated output for all 832 combinations of eight representative literals and thirteen binary operators. Targeted Unicode, builtin, short-circuit, JavaScript-reserved-name, structured-error, AST-location, optimizer-purity, and hostile handcrafted-identifier cases also passed.
- Independent checks exercised all four compile-size error paths, malformed limits, bytecode short-circuit and step limits, all 128 ASCII scanner inputs, and a 1,500-term expression through parse, interpret, and generated execution.

No production-suitability conclusion follows. Recursive phases, execution isolation, time/memory/output limits, cancellation, telemetry, release controls, and security review remain absent exactly as the candidate states.

## Learner usefulness

The specification is precise enough for an independent implementation and separates observable contracts from non-solution concepts. The TODO starter preserves the required API, the public suite samples all major phases without pretending to be exhaustive, milestones give a sensible order, and the design questions demand evidence. The reduced scanner debugging task and identifier-lowering review task reinforce two important failure modes without changing the main exercise. The bytecode alternative and candid production discussion add depth after the core path without burdening the initial learner view.

No candidate repair is recommended on the evidence available. Publication should remain blocked only on the external Node acceptance run and verified learner-view filtering described above.
