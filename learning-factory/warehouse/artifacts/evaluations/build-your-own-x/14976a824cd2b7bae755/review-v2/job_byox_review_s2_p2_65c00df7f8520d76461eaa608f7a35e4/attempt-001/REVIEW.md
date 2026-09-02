# Independent review

Verdict: **REVISE** (advisory only). CANDIDATE/ was inspected and tested without repair.

## Prioritized findings

### P1 — A normal run can remain permanently RUNNING after its runner completes

cmd_run releases the per-name lock before waiting, as required
(CANDIDATE/sealed/reference/tinybox.sh:285). After the runner returns it calls finish_run
(:293), which attempts a fresh lock acquisition (:163-175). That acquisition uses the same
fail-fast path as an ordinary competing command and exits immediately if the lock is held
(:99-106).

A concurrent run or delete may legitimately acquire the lock while the first runner is finishing.
It will eventually reject the RUNNING state, but the finishing controller can lose the lock race
first and abort without recording either exit_code or EXITED. A bounded reviewer harness made the
competing metadata read slow, released the controlled runner while that competitor held the lock,
and observed:

~~~text
PRIMARY_STATUS=3
COMPETITOR_STATUS=3
INSPECT_STATUS=0
name=collision
status=RUNNING
exit_code=
~~~

This violates the lifecycle and run completion requirements. The sealed concurrency test does not
cover the schedule: it waits for competing operations to finish before releasing the runner
(CANDIDATE/sealed/reference_tests/test_reference.sh:107-116). Completion must tolerate transient
cooperating contention, and a regression test must overlap runner completion with another mutation.

### P2 — The public name-safety check is a false positive on the starter

CANDIDATE/public_tests/test_contract.sh:58-63 reports success whenever traversal-shaped create
returns any nonzero status and no escape path appears. The starter's validate_name only rejects an
empty name (CANDIDATE/starter/tinybox.sh:22-27), then every nonempty create exits 70 as unimplemented
(:34-38). Direct observation was:

~~~text
$ bash CANDIDATE/starter/tinybox.sh create ../escape CANDIDATE/environment/fixtures/rootfs
tinybox: create is not implemented yet
# exit 70
~~~

The public suite nevertheless labels this as “a traversal-shaped name is rejected before path use.”
That overstates evidence and gives misleading learner feedback. The test should distinguish the
specified invalid-name rejection from a generic TODO or crash.

### P2 — The host-validation narrative contradicts itself

CANDIDATE/VALIDATION.md:181-197 records a successful final namespace integration on this host, and
the independent rerun also passed. CANDIDATE/sealed/REVIEW.md:20-21 still says the namespace runner
“was not proven runnable on this host.” The important portability and security caveats remain true,
but this stale host claim should be reconciled with the recorded result.

### P3 — Generated-material reuse terms are not explicit

The boundary between the CC0 catalog record and the linked NOASSERTION tutorial is clear, and the
candidate explicitly says linked content was not copied. However, “independently generated for
personal educational use” in PROVENANCE.json is a purpose statement, not a license grant, and no
license is supplied for the generated prose, scripts, or tests. If the pack is to be distributed or
modified beyond personal use, state the applicable terms explicitly.

## Assessment by review axis

- **Correctness:** The reference passes the supplied suites and a live host probe, but the
  independently reproduced completion race is a contract violation and requires revision.
- **Reproducibility:** Test harnesses use scoped temporary directories, outputs are deterministic,
  and builder transcripts largely reproduced. The live namespace test is necessarily host-specific.
- **Progressive disclosure:** Main answers, reference code, and non-public tests are structurally
  under sealed/ paths, including exercise-local answers. No materialized student view or
  transfer/isolation validation was supplied, so actual exclusion from learner delivery remains
  inconclusive and no transfer label is warranted.
- **License and provenance:** Project/source identifiers and commit metadata are internally
  consistent; the catalog/link boundary is candid. The source snapshot and upstream were
  unavailable, so extraction, licensing evidence, and the no-copy assertion could not be re-derived.
- **Learner usefulness:** The normative requirements, concept notes, staged milestones, design
  questions, safety warnings, and production caveats are strong. The false-positive public check
  weakens feedback at the first milestone.
- **Validation honesty:** GENERATED + PARTIAL, independent validation, no-fuzz, no-benchmark, and
  non-production claims are appropriately conservative. The stale live-runner sentence is the one
  material inconsistency found.

Only a separate orchestrator-captured acceptance validator may publish REVIEWED; this advisory
review does not do so.
