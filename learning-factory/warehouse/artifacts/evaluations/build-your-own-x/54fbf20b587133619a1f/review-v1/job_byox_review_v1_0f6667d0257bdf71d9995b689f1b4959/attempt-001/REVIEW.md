# Independent review

## Disposition

**REVISE.** The pack is thoughtfully structured and unusually candid about its partial validation,
but it is not ready to serve as independently validated learner/evaluator material. The two most
important gaps are that the evaluator-stage runners are wired to the sealed reference rather than the
learner implementation, and that progressive disclosure is asserted but not demonstrated by a
learner-view artifact or reveal policy. JavaScript correctness also remains unexecuted because neither
the generation record nor this review environment had Node.js.

This disposition does not treat the starter's deliberate `TODO`s as a failed learner submission. It
reviews whether the challenge pack, reference evidence, evaluator boundaries, and claims are fit for
their stated purposes. No validation label is promoted.

## Prioritized findings

### P1 — Evaluator-stage runners do not exercise the learner implementation

`sealed/adversarial/run.mjs:2-8` imports `run` and the public errors from
`../reference/index.js`. `sealed/benchmarks/benchmark.mjs:3-10` likewise imports every measured
operation from the reference. The sealed reference suite also imports the reference
(`sealed/reference_tests/pebble-reference.test.mjs:4-25`), appropriately for its explicitly stated
reference-only purpose. In contrast, only the deliberately incomplete public tests import
`starter/src/index.js`.

As wired, the documented adversarial command can pass while the learner implementation still consists
entirely of `NOT_IMPLEMENTED` paths, and the benchmark command measures the reference regardless of
the learner's work. The runners are useful reference self-checks, but they cannot be learner
completion, adversarial, or performance evidence. Provide a harness-controlled module-under-test
binding, run the oracle and learner separately, identify both artifact digests in captured results,
and ensure the learner cannot redirect the evaluator import.

### P1 — Progressive disclosure is not demonstrated or enforceable by this submission alone

`README.md:49-58` says the debugging, review, adversarial, and benchmark stages are outside the initial
learner view; `AGENTS.md:8-10` forbids reading those directories and `sealed/`. The submitted tree,
however, makes all of them readable beside the starter, including the complete reference,
reference tests, and six answer keys. `sealed/validation/check_artifact.py:16-40` actually requires
several sealed paths, so its static pass verifies the complete administrator pack, not a safe exported
learner view.

A complete administrator artifact may legitimately contain this material, so its presence is not by
itself proof that a real student view leaked. The missing evidence is the deterministic projection:
there is no allowlist, reveal-state mapping, exported learner artifact, or transfer test in the
submission. Instructions not to browse readable answers are not an isolation control. Generate and
independently inspect each stage view, with a default-deny rule for `sealed/`, before giving this pack
to learners.

### P1 — Core executable correctness remains unvalidated

`VALIDATION.md:17-27` honestly records that the visible/reference test command exited 127 and that no
JavaScript test, adversarial case, fuzz campaign, or benchmark ran. Independent attempts at the public
suite, reference suite, adversarial runner, and a minimal benchmark smoke invocation also exited 127:
no JavaScript runtime exists in this review environment.

The explicit Python 3.11 static pass is useful evidence for required paths, canonical metadata,
relative imports, selected forbidden-code patterns, and selected credential patterns. It is not
evidence that modules parse, APIs load, test expectations are correct, control-flow targets execute,
or error classes behave as documented. Before any correctness promotion, run the public and reference
suites plus the correctly targeted learner adversarial suite under a named Node.js 20+ build, with
bounded commands and durable stdout/stderr, exit codes, runtime version, and artifact hashes.

### P2 — `maxSteps` has contradictory parity semantics

`REQUIREMENTS.md:108-110` explicitly permits the two engines to consume their budgets at different
rates. Yet `REQUIREMENTS.md:158-160` requires both backends to agree on terminating programs, and
`starter/README.md:189` asks learners to compare outputs and error categories. The reference makes the
conflict concrete: the interpreter ticks once for the `emit` statement and once for its literal
(`sealed/reference/interpreter.js:26-34,71-95`), while the VM charges `CONSTANT`, `EMIT`, and `HALT`
(`sealed/reference/compiler.js:71-75,142-145,174-176` and `sealed/reference/vm.js:149-155`). Therefore
`emit 1;` with `maxSteps: 2` succeeds on the tree backend and raises `STEP_LIMIT_EXCEEDED` on the VM.

The sealed review exercise itself calls backend-specific cutoffs a high correctness issue when parity
includes resource errors. Define shared semantic fuel points, or explicitly scope backend parity to
runs that do not exhaust fuel and document `maxSteps` as backend-specific. Add exact-boundary tests.

### P2 — The numeric result domain is under-specified

`REQUIREMENTS.md:7-10` requires source literals to be finite and `REQUIREMENTS.md:114-116` requires
finite bytecode constants, but runtime arithmetic (`REQUIREMENTS.md:92-97`) does not say whether a
finite operation that overflows to `Infinity`, or later produces `NaN`, is a valid Pebble number. The
reference only checks operand `typeof` and returns JavaScript arithmetic results
(`sealed/reference/runtime-values.js:3-7,23-42`). `sealed/REVIEW.md:46-48` acknowledges the same risk.

Different reasonable learner implementations can therefore disagree while each follows part of the
contract. State whether all runtime numbers must remain finite and identify the error code if not; or
explicitly specify IEEE-754 non-finite semantics. Cover overflow, `Infinity - Infinity`, equality, and
both backends.

### P2 — The static-check command has an undeclared interpreter floor

The documented command is `python3 sealed/validation/check_artifact.py`. In this workspace,
`python3` is 3.6.8 and the checker exits 1 at `from __future__ import annotations`; it also uses modern
built-in generic annotations. Naming the provisioned Python 3.11.5 binary makes it exit 0. The builder
record did state that its own `python3` was 3.11.5, so this is a reproducibility gap, not evidence that
the historical transcript was fabricated. Declare a minimum Python version or make the checker
compatible with the supported evaluator environment. Also retain workspace context with transcripts:
the rerun saw no raw `.git`, whereas the builder's historical workspace saw one.

### P3 — Two staged exercises drift from the learner's declared interfaces

- `debugging/exercise-03/README.md:10-13` calls `compileBlock(node.thenBranch)`, but the normative
  `IfStatement` field is `consequent` (`REQUIREMENTS.md:69-70`). This can distract from the intended
  absolute-jump defect unless the alternate field name is explicitly declared hypothetical.
- `review_exercises/exercise-02/README.md:11-28` constructs
  `PebbleRuntimeError(message, "CODE")`, while the supplied learner class accepts a details object and
  reads `details.code` (`starter/src/errors.js:2-4,21-24`). Those snippets produce the default
  `RUNTIME_ERROR`; the sealed answer discusses prototype membership but not this API mismatch.

Align the excerpts with the starter or tell learners which additional defects they are expected to
review. This is lower severity than the evaluation gaps, but it affects exercise focus and answer-key
reliability.

## License and provenance assessment

The boundary is conservative and internally consistent. `PROVENANCE.json` identifies the catalog
snapshot and linked project, while `LICENSE_BOUNDARY.md:3-13` says the linked resource is context only,
records its license as `NOASSERTION`, disclaims copying, and grants generated material only personal
educational use. Independent strict-JSON parsing and canonical hashing matched the expected manifest
and provenance object digests.

Those hashes establish integrity of the supplied metadata, not authorship or non-copying. The linked
source/snapshot was unavailable in this offline review workspace, so the no-copy/no-close-paraphrase
assertion is inconclusive. The pack also supplies no general redistribution license; consumers should
honor the stated personal-use boundary rather than infer rights from the catalog's CC0 status.

## Positive evidence and claim honesty

- The manifest stays at `GENERATED`/`PARTIAL`, requires independent validation, and sets
  `productionized` to `false`.
- The validation and production notes explicitly deny unperformed test, fuzz, benchmark, security, and
  production-readiness claims.
- The normative requirements, starter interfaces, staged public tests, conceptual notes, and suggested
  implementation order form a useful learning path.
- Independent static checks found 68 regular files, no symlinks/special paths, four strict-JSON
  metadata/package files, 26 JavaScript modules, 46 resolved relative imports, no selected forbidden
  dynamic-code mechanism, and no high-confidence credential-pattern match.
- The sealed self-review openly records recursion, memory, bytecode data-flow, and non-finite-number
  risks. That candor is useful, though it is not independent validation.

## Minimum revision gates

1. Wire evaluator/adversarial and benchmark stages to the learner artifact under harness control while
   retaining separate reference self-tests.
2. Produce and inspect deterministic learner/stage views that prove sealed and unrevealed material is
   absent, then retain transfer evidence.
3. Run the JavaScript suites on Node.js 20+ with bounded, durable, artifact-bound logs.
4. Resolve the work-budget and numeric-domain contracts and align the two staged exercise snippets.

