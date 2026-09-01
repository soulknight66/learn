# Independent review

Verdict: **REVISE**

The pack is a strong advanced exercise with an unusually clear contract, useful conceptual scaffolding, honest validation language, and a functional sealed reference on ordinary inputs. It should not yet be accepted unchanged: one reference API behavior directly violates the published contract, deeply nested valid input escapes the documented error model, and the submitted artifact does not itself enforce the sealed/learner boundary.

The review was read-only with respect to `CANDIDATE/`. Its aggregate file-content SHA-256 was `b007464e59a00b94602a56b09724208aeba27b792d1b3dffc24e1e8e1e54a74f` both before and after checks.

## Prioritized findings

### P1 — The submitted tree does not enforce a learner/sealed boundary

`sealed/reference`, `sealed/reference_tests`, and all sealed answers are normal readable files beside `starter/`. `AGENTS.md` asks learners not to inspect them, but that is a social instruction, not isolation. The structure checker verifies naming placement inside the full tree; it does not build or test a learner projection. A wholesale copy of `CANDIDATE/` would disclose the implementation, evaluator cases, and answers.

Before learner release, provide a deterministic allowlist/projection owned by the harness and an independent test proving no `sealed/**`, hidden-test, answer, or reference content is reachable from the student view. If the factory already supplies that isolation outside this submission, its evidence was unavailable here and must be attached before promotion.

### P2 — Reusing the lexer violates the exactly-one-EOF API

`REQUIREMENTS.md` says `Lexer#scan_tokens` returns an array ending in exactly one `EOF` and does not declare lexer instances single-use. The reference appends an EOF on every call and returns its original mutable array. The independent probe observed:

```text
same_object=true
types=[:PRINT, :INTEGER, :SEMICOLON, :EOF, :EOF]
eof_count=2
```

The sealed internal review candidly mentions this, so it is not a validation-honesty issue, but it remains a correctness defect. Make scanning idempotent (or explicitly define and enforce single-use semantics) and add a deterministic regression test.

### P2 — Deep valid syntax escapes the Pebble error model

A source expression containing 10,000 unary `!` operators is valid under the stated grammar. A bounded probe raised `SystemStackError`, with `error.is_a?(Pebble::Error) == false`. The CLI would not catch this class. This also conflicts with the adversarial guide's instruction to exercise very long unary chains and nesting.

The candidate correctly records unbounded recursive depth and `productionized: false`, but the reference still needs an explicit deterministic nesting limit that raises a located `ParseError`, or a non-recursive strategy. Cover both unary and parenthesis nesting at the boundary.

### P2 — The provenance integrity field is not independently reproducible

The manifest's `provenance_sha256` is `e534f250...`, equal to `PROVENANCE.json`'s internal `snapshot_sha256`, but the actual file SHA-256 is `5119170b...`. No canonicalization or excluded-field algorithm explains how to recompute `e534f250...`. The structure script checks equality between the two recorded strings, not their relationship to supplied bytes. This does not by itself prove corruption, but the field cannot presently function as independently verifiable integrity evidence.

Document the digest domain and canonicalization, rename it if it identifies a source snapshot rather than the provenance file, and include a recomputable digest for the exported provenance artifact. Avoid the host-specific absolute source path; an immutable upstream URL plus commit/tree identity is more portable.

### P3 — Generated-material reuse terms remain ambiguous

The license boundary correctly keeps catalog CC0 separate from the linked article's `NOASSERTION` status and does not claim the article's license. However, “independently generated for personal educational use” is a classification, not a license grant, and there is no license or notice for the generated pack itself. State the generated material's owner and explicit reuse terms, even if the intended result is all-rights-reserved/internal-only.

The no-copying assertion could not be independently checked because neither the recorded source snapshot nor linked resource was available. It should remain a provenance assertion, not validation evidence.

## What held up

- The authored public/reference suite reproduced at 12 tests and 26 assertions with no failures; the sealed suite reproduced at 27 tests and 77 assertions with no failures.
- An independent harness passed 10 semantic groups covering tokens, locations, grammar, declaration timing, lexical scope, deterministic jumps, signed division/modulo, exact types, overflow, malformed bytecode, and step budgets. Its sole failure was the lexer-reuse defect above.
- The reference CLI produced `3\n2\n1\n`, usage exited 64, and a lexical error exited 1 with a located diagnostic.
- All 23 Ruby source/entrypoint files passed `ruby -c` on Ruby 2.5.9. No third-party dependency, symlink, common credential marker, dynamic evaluation, subprocess primitive, or network primitive was found by targeted inspection.
- The learner path is otherwise well staged: a compact overview leads to an authoritative contract, concepts, public foothold tests, debugging prompts, design questions, and code-review exercises. The starter's failure is intentional and clearly disclosed.
- Validation claims are restrained. `GENERATED`/`PARTIAL`, `productionized: false`, the unexecuted benchmark statement, and the explicit refusal to claim validator-controlled labels are all consistent with observations.

## Claim disposition

| Label or claim | Independent disposition |
|---|---|
| `GENERATED` / `PARTIAL` | Accurate description of the submission. |
| `BUILDS` / `TESTED` | Not promoted. Syntax and bounded executions were observed, but defects remain and the orchestrator controls labels. |
| `FUZZED` | No claim and no evidence. |
| `BENCHMARKED` | No claim. One reviewer smoke iteration only confirmed driver operation and its `UNVALIDATED_MEASUREMENT` label. |
| `REVIEWED` | This report supplies review evidence but does not mutate or promote the manifest. |
| `TRANSFER_VERIFIED` | No claim and no learner-transfer evidence. |
| `PRODUCTIONIZED` | Correctly false; resource, verifier, isolation, and operational gaps remain. |

## Disposition

Revise, then rerun independent checks. The core exercise does not need redesign; the required work is to enforce the disclosure boundary, close or explicitly redefine the lexer API edge, convert recursive exhaustion into a deterministic language error, and make provenance/license metadata independently interpretable.
