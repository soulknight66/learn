# Independent review

## Disposition

**REVISE.** The pack is unusually candid and educationally strong, and its Python-side structure and
learner projections reproduce cleanly. Two acceptance-critical gaps remain: the evaluator does not
isolate untrusted learner code from its sealed oracle, and no JavaScript runtime was available to
establish that the reference, tests, or harnesses execute as designed. The reference VM and hostile
nesting contract also need narrower corrections.

This verdict is advisory. It does not add or recommend adding a `REVIEWED` label to the candidate
manifest.

## Prioritized findings

### P1 — The evaluator boundary can be bypassed and cannot support trusted acceptance

`sealed/evaluator/bindings.mjs` scans source text with three regular expressions before importing the
learner module. Legal ECMAScript comments between tokens evade all three patterns. For example, from
`starter/src/index.js`, each of these can refer to the co-located sealed tree without being reported:

```js
import { run } from/* comment */ "../../sealed/reference/index.js";
import/* comment */ "../../sealed/reference/index.js";
const oracle = await import/* comment */("../../sealed/reference/index.js");
```

The independent probe observed `false` for every boundary regex on every example. This is not merely
a regex edge case:

- Candidate and oracle modules are loaded into the same Node process and share mutable globals and
  built-in prototypes.
- The full pack puts `starter/` and `sealed/reference/` under one readable root at evaluation time.
- `assertApi` checks only that required exports are functions.
- The adversarial runner obtains the expected error constructor from the candidate itself. A
  candidate that exports `Error` under each required error name can make an ordinary host error pass
  the current `instanceof` check if it supplies the expected `code`.
- Hashing before and after import proves content identity, not behavioral isolation or absence of
  oracle access.

The submitted starter contains no such escape and the locally projected learner view excludes
`sealed/`. The problem is that the acceptance harness is supposed to evaluate future untrusted
learner code, where a text scan is not a security boundary.

Required revision: run the candidate in a process and filesystem view from which the oracle and
administrator tree are unreadable, run the oracle independently, and compare serialized observations
in a harness-controlled parent. Treat import scanning as diagnostic defense in depth only. Add
regressions for comment-separated imports, built-in filesystem access, top-level side effects,
prototype mutation, false error-class exports, and a non-returning candidate under an outer timeout.

### P1 — Executable correctness remains unestablished

No Node.js, npm, or alternate JavaScript engine was present. Bounded attempts to run a public test,
the sealed reference suite, the adversarial runner, and the minimal benchmark command all exited
`127`. There is consequently no independent evidence for JavaScript syntax, ESM loading, reference
behavior, tree/VM parity, malformed-bytecode behavior, or timing.

The manifest and validation record handle this honestly: they retain only `GENERATED` and `PARTIAL`
and explicitly disclaim all executable labels. That honesty prevents this from being a false-claim
finding, but it still blocks acceptance as correct.

Required validation on Node.js 20 or newer:

1. Load every shipped ESM entry point.
2. Run the sealed reference tests and require a clean pass.
3. Confirm the incomplete starter produces the documented staged failures.
4. Exercise the adversarial and benchmark harnesses in copied packs containing controlled good,
   bad, escaping, and hanging candidate fixtures.
5. Capture commands, runtime version, exit status, stdout/stderr, and artifact identities outside the
   candidate's own prose.

### P2 — Reference bytecode validation is weaker than the published contract

The learner README says `execute` validates stack use before running bytecode. The sealed design notes
say the separate pass provides failure atomicity, and the review answer calls for reachable stack
depth with equal merge heights. In contrast, `validateBytecode` in `sealed/reference/vm.js` checks
envelope, field, opcode, constant, name, target, and terminal-`HALT` shapes only. Stack underflow is
checked later by `pop`, and residual height is checked only when `HALT` dispatches.

Thus malformed control flow can begin execution before its stack defect is found, and dead or
path-dependent stack defects need not be rejected by the prevalidator. This also leaves merge-height
inconsistency and stack-growing cycles outside the claimed verifier.

Required revision: either narrow the documentation to the actual dynamic guarantee or add a
control-flow dataflow verifier that checks stack requirements/effects, consistent merge heights, and
terminal height before dispatch. Add tests for underflow after prior valid instructions, divergent
branch heights, dead malformed stack operations, and stack-changing cycles.

### P2 — Host recursion leaks through the hostile-input boundary

The parser recursively handles grouping and unary chains; the evaluator and compiler recursively walk
expression trees. None imposes a nesting limit, and compilation is outside the execution budgets.
Deep input can therefore fail with a host `RangeError` before the documented `PebbleSyntaxError`,
`PebbleRuntimeError`, or `PebbleStepLimitError` boundary is reached. This conflicts with the requirement
that malformed input terminate within bounded resources and with the instruction to treat inputs as
hostile.

The sealed review already discloses this accurately. Resolve it by documenting and enforcing source,
token, AST-depth, bytecode, and output limits with typed errors, or by making the relevant walks
iterative. Run boundary and one-past-boundary cases under an outer process deadline.

### P3 — A benchmark report is not self-contained provenance

The revealable benchmark protocol asks for the exact command, commit, operating-system context, and
machine-load state. The JSON emitted by `sealed/benchmarks/benchmark.mjs` includes artifact hashes,
Node version, platform, architecture, settings, raw samples, and summaries, but not exact argv,
timestamp, OS release, source commit, or load note. Its README asks operators to record some of these
separately, so the implementation is honest but the output alone is not a reproducible measurement
record.

If the harness is retained, place these fields in one captured envelope (allowing an explicit
`unknown` load value). This is not a benchmark-result defect because no benchmark result is claimed.

## Verified strengths

- Manifest claims are conservative: `GENERATED`, `PARTIAL`, independent validation required, and
  `productionized: false`.
- The specification, API, AST, errors, budgets, and bytecode surface are detailed enough for a learner
  to implement without consulting the linked project.
- Starter omissions are explicit TODOs rather than disguised failures; public tests say they are
  incomplete examples.
- Debugging and review exercises are concrete, ordered, and paired with sealed answer keys. The
  revealable adversarial and benchmark material exposes protocols rather than exact answers/results.
- Independent reconstruction reproduced all five default-deny view identities. A real temporary core
  export contained exactly 25 regular files and no sealed, administrator-only, or later-stage roots.
- Metadata identifiers and canonical hashes are internally consistent. The license boundary correctly
  separates the CC0 catalog record from the linked resource's `NOASSERTION` license and makes no
  redistribution promise for generated material.
- Both supported Python interpreters reproduced the submitted static checker output, and all eight
  Python isolation/wiring tests passed.
- The validation prose clearly distinguishes static checks from builds, tests, fuzzing, benchmarks,
  transfer validation, review, and production readiness.

## Remaining evidence limits

The upstream source and catalog checkout were not readable here, so independent no-copy and upstream
license comparison was impossible. `PRIOR_BUILD` and `PRIOR_REVIEW` were also absent, preventing
reproduction of their historical hashes. The temporary view export was local implementation evidence,
not a check of the real delivery boundary.
