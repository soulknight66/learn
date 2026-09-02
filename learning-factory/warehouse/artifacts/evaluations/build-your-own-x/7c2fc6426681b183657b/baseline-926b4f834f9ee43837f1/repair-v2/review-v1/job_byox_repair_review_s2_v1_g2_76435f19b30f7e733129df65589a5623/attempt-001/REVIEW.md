# Independent review

## Advisory verdict

**PASS.** No blocking correctness, safety-boundary, learner-usefulness, or claim-honesty defect was
found. This verdict is advisory only: it does not modify `CANDIDATE/MANIFEST.yaml`, and only the
orchestrator-captured acceptance validator may publish `REVIEWED`.

## Prioritized findings

1. **P0/P1/P2 — none found.** The repaired numeric classifier now establishes the complete token
   shape before range conversion (`sealed/reference/forth.S`, lines 426–494). Both permanent
   overflowing-prefix regressions (`sealed/reference_tests/test_reference.py`, lines 62–70) and an
   independent direct reproducer returned `7\n8\n`. Static review found pre-write checks for input,
   data stack, dictionary, code arena, patch stack, and return stack, plus the required signed
   division trap checks.
2. **P3 — learner-view isolation still depends on the control plane.** The full review artifact
   intentionally contains `sealed/`. Learner-facing material consistently treats it as evaluator
   content, and the audit found no reference/answer path in the unsealed exercise surface. A
   separately materialized learner view was not available, so exclusion remains a transfer
   prerequisite rather than a property proven by this pack.
3. **P3 — provenance is internally consistent but externally unverifiable here.** Manifest IDs and
   snapshot digest match `PROVENANCE.json`, and the candidate clearly distinguishes catalog CC0 from
   the linked resource's `NOASSERTION` status. The source snapshot and upstream link were unavailable,
   so clean-room similarity and license evidence cannot be authenticated. There is also no top-level
   license granting rights beyond the stated personal educational use.
4. **P3 — reproducibility is environment-scoped.** Two clean reference builds were byte-identical and
   matched the submitted hash, but the build uses host `/usr/bin/as` and `/usr/bin/ld.bfd`. Their exact
   versions are recorded; an immutable configured x86-64 binutils root was not supplied.

## Correctness and reproducibility

- Reference builds were byte-identical at
  `b3e847dcfb3579a3a0029836ca3ea590076cad4399d714beae4ac38a95878092`.
- Public tests passed 10/10, sealed boundary tests passed 14/14, and tooling regressions passed 6/6.
- A reviewer-authored model checked 830 arithmetic, signed-division, comparison, and bitwise results.
  Additional cases covered every byte `0x00`–`0x20` as a separator, near-numeric names, stack words,
  nested compilation, 15 deterministic failures, and 300 seeded arbitrary-byte inputs.
- The reference produced identical results natively and under the configured QEMU invocation.
- The output is a static x86-64 ELF with `_start`, no dynamic section, and non-executable stack.
- The candidate tree digest was unchanged by review.

These results independently support the candidate's local build and test observations, but do not
promote any manifest label.

## Progressive disclosure and learner usefulness

The exercise exposes a precise observable contract, a small buildable stub, staged milestones,
conceptual explanations, design checkpoints, public examples, debugging prompts, and review
exercises. Evaluator answers and the working oracle are consistently placed under `sealed/`. The
public tests are explicitly described as examples rather than the specification, which helps avoid
teaching to the visible suite. The intentional stub failure is clearly documented and is consistent
with `GENERATED` + `PARTIAL`.

## Validation and claim honesty

The validation record distinguishes historical worker evidence from independent validation, retains
the earlier failed workspace-preparation observation, calls the benchmark result
`UNVALIDATED_MEASUREMENT`, and explicitly disclaims `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, and `PRODUCTIONIZED`. The manifest remains conservative. No
unsupported promotion was found.

## Acceptance limitations

Before publication, the orchestrator should enforce the learner/sealed view split. A future artifact
intended for redistribution should add an explicit generated-material license, and a stronger
reproducibility claim should pin x86-64 binutils. No fuzzing, production, security, or performance
label follows from this review.
