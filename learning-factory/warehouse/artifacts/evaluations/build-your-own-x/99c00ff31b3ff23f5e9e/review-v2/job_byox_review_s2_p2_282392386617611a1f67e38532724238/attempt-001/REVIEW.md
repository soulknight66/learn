# Independent review

Verdict: **REVISE**.

The artifact has a strong educational shape, conservative validation labels,
and a largely coherent reference implementation. Clean builds and all 23
builder-authored reference/adversarial tests reproduced, and an independent
250-expression oracle check found no ordinary arithmetic or code-generation
disagreement. Two blocking issues remain: an observable I/O contract violation
and validator subprocesses that do not meet the repository's process-group
containment invariant.

## Prioritized findings

### P1 — Output write failures return success

`REQUIREMENTS.md:13-15` says a writing failure exits 66. The interpreter ignores
the return from `printf` at `sealed/reference/pebble.c:1044-1048`, and generated
programs ignore the return from `printf` emitted at
`sealed/reference/pebble.c:1240-1246`. Neither path checks the final stdout
flush.

An independent program containing 1,000 `print 1234567890;` statements was run
with stdout connected to `/dev/full`. Both `eval` and the linked generated
program returned 0 and emitted no diagnostic. The reference therefore violates
an explicit observable status contract. `sealed/REVIEW.md` honestly discloses
the unchecked calls, which is good claim hygiene, but disclosure does not make
the implementation conforming.

Required revision: detect print/flush failures in both backends, choose the
documented status 66 consistently, and add interpreter/native tests using a
deterministic failing output sink.

### P1 — Test timeouts do not contain process descendants

The public, adversarial, sealed-reference, benchmark, and environment runners
all call `subprocess.run(..., timeout=...)`, but none starts a new session or
terminates a process group. This conflicts with the repository invariant that
subprocesses use process groups. It is especially material in
`public_tests/run_tests.py`, which executes learner-controlled binaries.

Killing only the direct child does not contain a forked descendant. A descendant
can retain the captured stdout/stderr pipes, outlive the nominal timeout, and
prevent deterministic completion. Captured output is also accumulated without
a size bound.

Required revision: run each child in its own process group/session, terminate
the group on timeout with a bounded escalation, and cap retained output. Add a
containment regression using a helper that spawns a descendant and holds the
pipes open.

### P2 — A sealed `%` edge case is absent from the public contract

`REQUIREMENTS.md:49-52` explicitly identifies `INT64_MIN / -1` as overflow and
separately says division or remainder by zero is erroneous. It does not define
`INT64_MIN % -1`. The reference groups `/` and `%` together at
`sealed/reference/pebble.c:969-979` and returns runtime overflow for both; the
sealed test suite also requires `% -1` to fail.

A learner can reasonably read the stated contract as allowing the
mathematically representable remainder 0. Hidden validation must not impose an
unstated semantic choice.

Required revision: either state explicitly that both operators reject the
`INT64_MIN, -1` pair, or define `%` as 0 and adjust the reference and sealed
test. Include the chosen signed-division/remainder rule in learner-facing
concept material.

### P2 — Payload integrity and the final hygiene transcript are incomplete

`sealed/reference_tests/verify_artifact.py:44-47` pins hashes only for
`MANIFEST.yaml` and `PROVENANCE.json`; it does not authenticate the reference,
tests, requirements, or learner files. The submitted `PROVENANCE.json` hash is
`a923b5d3...`, while `MANIFEST.yaml`'s `provenance_sha256` is instead the value
of the embedded source-snapshot field. That may be intentional, but the digest
target is not defined in learner-facing metadata and the source snapshot needed
to recompute it is absent.

The verifier currently observes 48 text files, whereas `VALIDATION.md:114-120`
records 49 after purported final cleanup. Builds and test counts otherwise
reproduced.

Required revision: define what every provenance digest covers, publish a
deterministic artifact-wide file/digest inventory, and refresh final validation
against the exact submitted tree.

### P3 — A revealed review answer conflicts with the reference's error order

`sealed/review_exercises/symbol_resolution/sealed/ANSWER.md` says duplicate
declarations must be rejected before resolving the initializer. The reference
does the reverse at `sealed/reference/pebble.c:864-895`. Consequently,
`let x=1; let x=missing;` reports unknown `missing`, not the duplicate. Both
conditions make the program invalid, and the public contract does not specify
diagnostic precedence, but the answer presents its order as an invariant.

Required revision: align the answer, reference, and any intended diagnostic
precedence so progressively revealed guidance does not teach a different oracle.

## Correctness and reproducibility evidence

- The declared GCC 8.5.0, GNU Make 4.2.1, Python 3.6.8, and x86-64 environment
  reproduced.
- Clean starter and reference builds passed with strict warnings as errors.
- Public/reference/adversarial suites passed 6/6, 10/10, and 7/7 against the
  sealed reference.
- Exact accepted/rejected boundaries reproduced for expression depth 128/129,
  parenthesis depth 128/129, block depth 128/129, and variable count 256/257.
- A deterministic seed-20260902 sample of 250 bounded expressions matched an
  independent Python oracle in both interpreted and linked native execution.
- The ASan/UBSan compilation reached link and failed for the documented missing
  runtime libraries, so no sanitizer execution is credited.

The starter's six public-test failures are expected: it is explicitly a
buildable, incomplete exercise scaffold. They are not treated as a false
implementation claim.

## Learner usefulness and progressive disclosure

The progression from requirements to concepts, design questions, starter,
public smoke tests, and sealed answers is clear. The learner-facing README is
honest that the public suite is not comprehensive. Sealed references and answers
are structurally separated, and no symlink or solution-bearing file was found in
the declared learner paths.

The scaffold is nevertheless steep: beyond a lexer API it provides no parser,
AST, resolver, evaluator, or backend interfaces, and all public checks are
end-to-end failures initially. Incremental lexer/parser/resolver tests or staged
interfaces would give learners useful feedback before the full compiler works.
The local artifact also does not demonstrate how validator-only paths are
actually excluded from a student view; that isolation remains the harness's
responsibility.

## License, provenance, and claim honesty

The boundary is stated conservatively: CC0-1.0 is attributed to catalog
metadata, the linked learning resource is `NOASSERTION`, and no rights in that
resource are claimed. The generated material is described only as independently
generated for personal educational use; this is not an explicit redistribution
license and should be clarified before publication.

Project/source identifiers and commits are internally consistent. The upstream
snapshot, license evidence, and linked repository were unavailable locally, so
the no-copy assertion and source hashes remain unverified claims rather than
independent evidence.

The manifest is appropriately restrained: `GENERATED`, `PARTIAL`, independent
validation required, and `productionized: false`. It does not claim BUILDS,
TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED.
This review does not promote any label; only the orchestrator-controlled
acceptance validator can do so.
