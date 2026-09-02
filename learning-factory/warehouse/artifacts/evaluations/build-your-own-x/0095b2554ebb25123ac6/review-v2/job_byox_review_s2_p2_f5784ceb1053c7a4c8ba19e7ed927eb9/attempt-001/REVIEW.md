# Independent review

Advisory verdict: **PASS** for the submitted `GENERATED` + `PARTIAL` scope. This
is not a build or behavioral attestation, and only the factory's separate
acceptance validator may publish `REVIEWED`.

## Prioritized findings

1. **P1 — Dynamic correctness remains unverified.** No Go executable or
   substitute compiler is installed. All six 30-second-bounded `go test ./...`
   attempts exited 127 before loading a package. Consequently, the scaffold's
   compilability and the reference implementation, public/reference tests, CLI,
   fuzz targets, and benchmarks remain inconclusive. The candidate reports this
   honestly and keeps only `GENERATED` and `PARTIAL`; a Go-capable acceptance
   harness must run the documented module tests before granting any execution
   label.

2. **P2 — Define `string-character` in the normative grammar.**
   `CANDIDATE/REQUIREMENTS.md` uses that nonterminal without defining it. The
   sealed lexer statically appears to accept any valid UTF-8 byte sequence inside
   a string except an unescaped quote or backslash, including raw line breaks and
   control characters. State that policy explicitly so learner implementations
   and hidden edge tests cannot make different reasonable choices.

3. **P2 — Broaden independent acceptance coverage.** The checked-in suites are
   thoughtful but no test source exercises the command-line contract end to end.
   The adversarial inventory also calls out short-count writers and unreachable
   invalid opcodes, while the sealed tests cover a writer returning an error and
   reachable corrupt opcodes. A validator should add CLI mode/stdin/argument/exit
   checks, maximum-instruction boundaries, short writes, and unreachable corrupt
   bytecode. This is a coverage gap, not evidence that those paths fail.

4. **P3 — Keep validation non-mutating.** The historical command in
   `CANDIDATE/VALIDATION.md` begins with `gofmt -w`. It did not mutate anything on
   the builder host because `gofmt` was missing, but an independent immutable-input
   check should use `gofmt -d`/`gofmt -l` or format a disposable copy.

5. **P3 — External provenance claims remain externally unconfirmed.** Project,
   source, commit, snapshot, and canonical JSON identifiers are internally
   consistent. The boundary clearly assigns CC0 to the catalog record and
   `NOASSERTION` to the linked project. The upstream snapshot was not available,
   however, so this review cannot independently establish the asserted no-copy
   boundary or source license evidence.

## Dimension assessment

- **Correctness evidence:** Static phase boundaries, stack effects, lazy control
  flow, arithmetic checks, source spans, and defensive verification are coherent.
  Test source covers representative semantics and adversarial cases. None of it
  substitutes for Go execution.
- **Reproducibility:** Go 1.20+, standard-library-only dependencies, local module
  replacements, deterministic seeds, explicit limits, and exact commands are
  documented. The current host cannot complete the Go portion.
- **Progressive disclosure and isolation:** The learner entry point, normative
  contract, public tests, design prompts, and advanced exercises are separated
  sensibly. Every answer/reference artifact is below a `sealed` path segment, and
  no solution file was found in the simulated learner-visible inventory. Actual
  view exclusion remains an orchestrator responsibility.
- **License and provenance:** The records are strict JSON despite the manifest's
  `.yaml` suffix, their pinned canonical digests reproduce, and their durable IDs
  agree. The linked resource's unknown license is not presented as a grant.
- **Learner usefulness:** The project offers a clear milestone sequence, stable
  scaffold API, black-box public tests, conceptual notes, design questions,
  debugging tasks, review exercises, and explicit warnings against overfitting.
- **Validation honesty:** The candidate expressly disclaims build, test, fuzz,
  benchmark, review, transfer, and production conclusions. Its manifest does not
  overstate the available evidence.

## Required acceptance follow-up

On a clean Go 1.20+ host, run the four primary module suites in
`starter`, `public_tests`, `sealed/reference`, and `sealed/reference_tests`, plus
the two debugging exercise suites. Run CLI black-box checks separately. Fuzz and
benchmark only if those results will be captured and labeled as such. Preserve
the submitted candidate unchanged throughout validation.
