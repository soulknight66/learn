# Independent review

Verdict: **REVISE**. The core C/Arm teaching implementation is technically strong and its modest validation claims reproduced unusually well. Revision is still warranted at the publication and harness boundaries below. This verdict does not grant a `REVIEWED` label.

## Prioritized findings

### P1 — The official learner view drops the generated-material license boundary

`environment/student_view_policy.json` allowlists six root files but omits `LICENSE_BOUNDARY.md`. The strict reviewer-materialized view therefore passed while containing no statement that the generated material is all rights reserved, grants no redistribution/reuse license, and is authorized only inside the learning environment. `AGENTS.md` warns about the linked repository's unasserted license, but that is a different boundary.

Impact: a learner receives the work without the pack's controlling reuse notice. That weakens license/provenance transparency precisely at the publication boundary.

Required revision: include `LICENSE_BOUNDARY.md` in the learner policy, or place an equivalent generated-material notice in an already allowlisted root document and test for its presence. The upstream URL itself can remain evaluator-only if disclosure would encourage solution copying.

### P1 — The adversarial subprocess timeout does not control a process group

`adversarial/run_vectors.py:172-175` uses an argv array, captured output, and a five-second timeout, but it does not create and terminate a process group. Python's `subprocess.run(..., timeout=...)` kills the direct child only. This misses the workspace invariant requiring process-group control and would not contain descendants if the runner or a future candidate-backed executable spawned any.

Required revision: use a bounded `Popen` flow that starts a new session/process group, kills the whole group on timeout, waits for cleanup, and retains bounded stdout/stderr. Add a deterministic regression helper that spawns a descendant and proves timeout cleanup.

### P2 — The submitted pack audit is not reproducible from the submitted pack

`sealed/pack_audit.py:216-218` unconditionally reads `PRIOR_BUILD/PROVENANCE.json`, and lines 229-238 also require the external prior tree. `CANDIDATE/` does not contain that control input. Running the exact documented command against the submission exits 1:

```text
pack_audit: FAIL: metadata parse failure: ... CANDIDATE/PRIOR_BUILD/PROVENANCE.json;
manifest does not equal the authoritative object; unexpected omitted prior files: []
```

The manifest diagnostic is also inaccurate: the broad metadata exception sets `manifest = None` merely because the prior provenance is absent. Independent parsing confirmed that the submitted manifest equals the script's authoritative object.

Impact: preservation against the prior pack and the builder's headline pack-audit PASS remain non-reproducible for a separate reviewer, and the failure output obscures what did and did not validate.

Required revision: make the prior baseline an explicit optional/required CLI input with a recorded artifact digest, separate self-contained current-pack checks from historical-diff checks, and isolate parsing errors so current manifest validation still reports accurately.

### P2 — Post-attempt progressive disclosure has prose but no deterministic view definition

`debugging/README.md` says an exercise can be revealed after an attempt, and `review_exercises/` similarly separates a candidate fragment from a sealed answer. The sole policy excludes both roots entirely and supplies no stage-two allowlist or materializer. Copying either directory naively would also copy its nested `sealed/` answer.

Impact: the initial view is safely auditable, but the advertised later learning stages are not reproducible or safe-by-construction.

Required revision: define separate machine-readable policies for each reveal stage, materialize only the intended fixture/prose, and run the same strict inventory audit on every stage.

## Confirmed strengths

- Validation labeling is honest: the manifest remains `GENERATED`/`PARTIAL`, productionization is false, and the prose explicitly disclaims stronger labels.
- The initial learner allowlist works. A strict view had 55 entries and no sealed/reference material; extra-root and symlink mutations were rejected.
- The reference passed 407 bundled checks, 12 schema-checked adversarial vectors, the public suite, and 86 independent boundary checks under ASan/UBSan.
- Clean Arm builds were byte-reproducible. ELF structure, undefined symbols, and the complete bounded QEMU marker sequence independently matched the record.
- Requirements, concepts, public tests, design questions, explicit non-goals, and visible starter stages form a useful core learning path without disguising host tests as hardware evidence.
- Full-pack provenance text clearly separates CC0 catalog metadata from the unlicensed linked resource and makes no unsupported production, fuzzing, benchmark, transfer, or hardware claim.

## Advisory conclusion

No core reference defect was found in the exercised scheduler, VM, RAMFS, boot, MMU, UART, or cooperative context path. The requested revisions concern deterministic publication, license visibility, validation reproducibility, and subprocess containment. A separate orchestrator-controlled validator must decide acceptance and any later `REVIEWED` promotion.
