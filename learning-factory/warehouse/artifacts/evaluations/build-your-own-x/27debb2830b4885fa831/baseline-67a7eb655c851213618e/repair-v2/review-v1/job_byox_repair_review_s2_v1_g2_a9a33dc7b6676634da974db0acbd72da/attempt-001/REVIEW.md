# Independent review

## Verdict

**PASS (advisory).** I found no repair-required correctness, disclosure, reproducibility, or
validation-honesty defect within the candidate's explicitly limited `GENERATED` + `PARTIAL` state.
This verdict neither changes the manifest nor awards `REVIEWED` or any other validation label.

## Prioritized findings

1. **P1 publication precondition — redistribution is still blocked.** The generated material has
   no affirmative license. `LICENSE_BOUNDARY.md`, `MANIFEST.yaml`, and the productionization notes
   say so consistently. This is not a hidden defect in the current personal-education artifact, but
   an authorized license decision and an updated release boundary are mandatory before transfer or
   publication.
2. **P2 provenance limitation — external claims were not independently established.** Manifest and
   provenance identifiers and hashes are internally consistent, but the catalog snapshot and linked
   upstream repository were not available in this workspace. The statements that linked content was
   not copied and that the recorded source commit is authoritative therefore remain assertions, not
   independently reproduced facts.
3. **P2 hardening limitation — this is deliberately not productionized.** Recursive parsing/tree
   evaluation, unbounded source/string/output memory, dynamic rather than whole-CFG bytecode checks,
   and a single-runtime compatibility result remain. The candidate discloses these limits and makes
   no `PRODUCTIONIZED`, fuzzing, benchmarking, or security-certification claim.
4. **P3 baseline interpretation — learner tests intentionally start red.** The untouched starter
   passes lexical tests and fails parser/execution tests at explicit TODOs. Documentation states this
   clearly, so the failure is useful staged scaffolding and not evidence of a broken runner. It must
   not be reported as a passing learner implementation.

No P0 or repair-required P1 finding was identified.

## Correctness and reproducibility

- The grammar, span model, block scope, initializer order, truthiness, value rules, compiler stack
  effects, jump patching, and tree/VM diagnostic parity agree across source inspection, 14 direct
  reference tests, 6 adversarial tests, and an independent 1,620-check operator matrix.
- A separate VM probe rejected malformed constants, arrays, opcodes, operands, jumps, stack/scope
  states, spans, loops, and accessor-backed fields with `E_INVALID_BYTECODE`; the accessor getter was
  not invoked. Valid handcrafted control flow executed correctly.
- Parser, interpreter, compiler, and VM input graphs remained unchanged in a focused mutation probe.
- Both reference CLI backends printed `12` for `starter/example.mica`. All JavaScript parsed under the
  exact pinned Node v22.21.0 binary, with no package installation or network access.

## Progressive disclosure and learner usefulness

The learner projection is a strict top-level allowlist. An independently copied sibling projection
matched 25 files and 4 directories byte-for-byte, with no `sealed` component; its inventory digest
was `9122c9f6206a5d3df1964ed50dd261272b9dbf00bc5d6b8957b8b52134790d43`.
Reference code, instructor tests, exercise answers, provenance/validation evidence, and advanced
review material remain outside that projection.

The learner path is coherent: an observable contract, concepts, design questions, staged TODOs,
public examples, a working lexical layer, and an executable sample. Public tests are intentionally
small and explicitly disclaim completeness. Instructor-side debugging and review exercises add
useful follow-on material without exposing their answers to the base learner view.

## Validation honesty

The manifest claims only `GENERATED` and `PARTIAL`, keeps `productionized` false, and requires
independent validation. Builder evidence distinguishes passing reference checks from the expected
failing starter baseline and expressly declines fuzzing, benchmarking, transfer, review, and
production labels. Independent reruns matched its material observations. The submitted verifier
scripts were treated as test subjects, not as proof by themselves.

## Recommendation

Accept this review for the candidate's current partial educational-artifact scope. Do not publish,
transfer, relabel, or present the starter as implemented until the controlling harness separately
resolves licensing, materializes and accepts the learner view, and performs any validation required
for stronger labels.
