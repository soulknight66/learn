# Independent review

Verdict: **REVISE**. The repaired toolchain binding, archive boundary, reference
behavior, and deterministic limits reproduced successfully. One validation-
integrity defect should be corrected before an advisory PASS.

## Prioritized findings

1. **P2 — The sanitizer claim contradicts the authoritative validation
   record.** `CANDIDATE/sealed/reference_tests/README.md:19-21` says the same
   checks “run in the documented sanitizer rerun,” but
   `CANDIDATE/VALIDATION.md:219-222` says no sanitizer was run in generation 2
   and that prior-generation observations were not reused. This is an
   affirmative evidence claim, not merely a suggested command. Reword it as a
   conditional (“would exercise the same cases”) or add generation-specific,
   reproducible sanitizer evidence. The independent reviewer sanitizer run
   documented in `VALIDATION.md` does not retroactively make the builder's
   archival claim accurate.

2. **P2 release gate — Never publish this complete archive as the learner
   view.** `CANDIDATE/sealed/` contains the reference implementation, private
   tests, design answers, and review answers. The submission clearly discloses
   this and does not claim transfer verification, which is good. Nevertheless,
   no projected student artifact was supplied for review, so an
   orchestrator-controlled projection excluding the entire sealed tree remains
   mandatory.

3. **P3 — Learner feedback becomes sparse after the lexer milestone.** The
   starter, requirements, concepts, and lexer-only mode form a useful first
   milestone, but the public suite has no `--emit`, malformed-bytecode,
   deterministic-limit, or tower check. The omission is honestly documented
   and validator coverage is substantially stronger; adding one or two
   intermediate learner-visible bytecode/VM checks would reduce the jump from
   a working lexer to the complete interpreter.

## Evidence supporting the implementation

- Pinned GCC/linker resolution and all three strict C17 builds succeeded in a
  writable copy, without modifying `CANDIDATE/`.
- Submitted tests reproduced the stated 2 lexer passes/8 skips, 10 public
  passes, 26 direct VM passes, and 21 sealed Python passes.
- Reviewer-owned tests added 21 black-box and 9 direct-VM assertions. They
  exercised exact source/code/depth/local/identifier/stack limits, malformed
  bytecode, conditional jump validation, arithmetic and short-circuit
  behavior, budget accounting, and the `4242` tower.
- GCC static analysis reported no diagnostics. The 30 reviewer assertions also
  passed an ASan+UBSan build; leak detection was disabled, so this is bounded
  supporting evidence rather than a sanitizer or production label.
- Manifest/provenance identifiers and recorded digests are internally
  coherent. The archive contains only regular files/directories, no build
  debris, and no match for the limited credential patterns checked.

## Boundaries

The catalog is recorded as CC0-1.0 while the linked tutorial remains
`NOASSERTION`; the pack makes no broader third-party license claim. The source
snapshot was not available to this reviewer, so independent copying and license
traceability could not be established. Generated material is described for
personal educational use, and redistribution still needs a separate rights
review as the submission itself states.

This verdict does not confer `REVIEWED`, `TESTED`, `FUZZED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED`. Only an orchestrator-captured
acceptance validator may publish a review label.
