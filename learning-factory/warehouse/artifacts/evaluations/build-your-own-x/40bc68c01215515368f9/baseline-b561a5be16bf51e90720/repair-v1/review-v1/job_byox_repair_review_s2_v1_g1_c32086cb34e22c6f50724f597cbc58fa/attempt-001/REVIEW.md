# Independent review

Verdict: **PASS (advisory)**. No blocking defect was found within the candidate's explicitly
`GENERATED` + `PARTIAL` scope. This verdict does not publish `REVIEWED`; only the separate
orchestrator-controlled acceptance validator may do that.

## Prioritized findings

### P0/P1 — none

Static review and bounded independent execution found no critical or major correctness defect. The
reference compiled cleanly, the public and sealed suites passed, and reviewer-authored probes covered
the repaired numeric boundary, exact semantic budget boundary, engine parity, whole-program bytecode
validation, and tick-free malformed cycles.

### P2 — learner-view isolation remains a required external publication gate

The full submission intentionally contains complete answers and tests under `CANDIDATE/sealed/`.
No solution-named path was found under `starter/`, `public_tests/`, or `environment/`, so the internal
layout supports progressive disclosure. It does not by itself prove that an exported student view
excludes the sealed tree. The manifest and candidate validation disclose this accurately. A transfer
validator must reject any learner view containing `sealed/`, reference sources/tests, review answers,
or equivalent material.

### P3 — the supplied runners assume a writable repository root

Both shell runners create `.mica-*` directories in the current directory. Direct public-runner
execution therefore failed in this deliberately read-only review staging tree before compilation.
Reproducing the same `javac` and `java` argv in guarded reviewer-owned temporary directories succeeded.
This is an environmental reproducibility constraint, not evidence of a code failure; using an
explicit external build directory would make the runners usable against immutable submissions too.

### P3 — provenance is transparent but externally uncorroborated

`PROVENANCE.json`, `MANIFEST.yaml`, and `LICENSE_BOUNDARY.md` agree on the project/source identities,
catalog `CC0-1.0` metadata, linked-resource `NOASSERTION`, and the assertion that linked content was
not copied. The present files reproduce the builder-recorded hashes. The upstream snapshot and
license evidence were not available, so those historical assertions cannot be independently proven
here. The generated-material wording covers personal educational use; broader redistribution would
still need an explicit licensing decision.

### P3 — production and hostile-resource boundaries remain intentionally open

Recursive parsing/tree evaluation and unbounded source, token, AST, string, and output allocation can
reach host resource limits. There is no cancellation hook, fuzz evidence, benchmark evidence, or
production isolation. These are candidly documented in the sealed review and productionization plan,
and the manifest does not claim `FUZZED`, `BENCHMARKED`, or `PRODUCTIONIZED`.

## Review dimensions

- **Correctness:** The contract is precise, the two engines are genuinely distinct after the shared
  front end, and the exercised success/error semantics agree. Independent checks observed 9/9 public,
  18/18 reference, 10/10 reviewer semantic, and 5/5 reviewer bytecode probes passing.
- **Reproducibility:** Exact dependency-free Java 21 tooling is documented. Two clean compilations
  produced identical sets of 47 class files and the same aggregate digest.
- **Progressive disclosure:** Learner-facing roots contain scaffolding, examples, and prompts rather
  than reference sources. Physical separation is good; export isolation remains unverified.
- **License/provenance boundary:** The catalog, linked resource, and generated work are distinguished,
  and no license is inferred for the linked resource. External corroboration was unavailable.
- **Learner usefulness:** The staged milestones, executable smoke tests, grammar/semantics contract,
  concept explanations, design questions, adversarial prompts, and review/debugging exercises form a
  coherent high-difficulty project. The five core TODO areas are clearly identified.
- **Claim honesty:** Builder evidence is explicitly labeled builder-controlled. `MANIFEST.yaml`
  remains `GENERATED` + `PARTIAL`, `productionized` is false, and stronger validation labels are not
  claimed. Benchmark and production documents state that their work was not executed.

## Recommendation

Accept this repaired candidate for the next orchestrator-controlled gate. Before any learner release,
validate an actual exported view and keep the full sealed package inaccessible. Do not infer fuzzing,
benchmarking, transfer verification, production readiness, or a published `REVIEWED` label from this
advisory PASS.
