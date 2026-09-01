# Independent review

Verdict: **REVISE**

The pack is unusually candid and the documented happy-path results reproduce, but it has two observable contract defects and a broken first learning checkpoint. Progressive-disclosure transfer is also not independently demonstrable from this workspace. These are revisions, not grounds to discard the pack: the core reference, documentation, tests, and validation labeling are otherwise solid.

## Prioritized findings

### P1 — `wait` overrides the status required by R4.4

`CANDIDATE/sealed/reference/src/jobs.c:294` first selects the correct highest-numbered completed job status, but lines 295–299 discard completed jobs and then replace that result with 1 whenever any stopped job remains.

A reviewer-owned deterministic harness added job 1 as stopped and job 2 as completed with exit status 7. `msh_jobs_wait_all` emitted `msh: wait: remaining jobs are stopped`, returned 1, and retained job 1. R4.4 says `wait` waits for running jobs and returns the last-command status of the highest-numbered completed retained job, which is 7 in this case.

Preserve the selected completed-job status when stopped entries remain, add mixed-state ordering tests, and explicitly specify the stopped-only result if status 1 is intended there.

### P1 — the advertised parsing milestone has no passable parsing checkpoint

The learner flow separates parsing from execution: `README.md` calls parsing milestone 1 and processes/pipes milestone 2, while `starter/README.md` directs learners to implement `parser.c` first. All three `ParsingTests` in `public_tests/test_shell.py`, however, require successful external-command execution.

To isolate the dependency, the reviewer linked the sealed parser with the unchanged starter shell and jobs modules. The resulting binary passed both invocation tests, proving the baseline was sound, but failed all three parsing-stage tests only with `msh: executor milestone is not implemented`. A learner can therefore implement the parser correctly and still receive no passing stage-1 feedback.

Provide a public parser-only harness against the supplied API, or redefine and document the stages so that the first tested milestone includes the minimum executor it needs.

### P2 — the reference accepts more whitespace separators than R2.1

`CANDIDATE/sealed/reference/src/parser.c:175` uses `isspace`. In the observed C runtime that includes vertical tab, form feed, and carriage return, while R2.1 names only unquoted space, tab, and newline as separators.

For each extra byte, the reviewer passed one argument containing `a<byte>b` to `printf '<%s>\n'`. The reference returned 0 but emitted two arguments as `b'<a>\n<b>\n'`, rather than preserving the byte in one argument. Use an explicit contract predicate and add byte-level cases for `\v`, `\f`, and `\r`.

### P2 — pipeline wiring fails when a standard descriptor starts closed

With fd 0 closed before launch, the first pipe can allocate fd 0. The downstream child calls `dup2(0, 0)`, then `close_pipes` closes fd 0 as an original pipe endpoint (`shell.c:318–327`). The reviewer ran `printf x | cat` in this state; it returned 1, produced no stdout, and `cat` reported `Bad file descriptor`.

The candidate commendably lists initially closed descriptors among reserved hardening cases, but the behavioral contract does not exclude this environment and R3.3 still requires the connection. Preserve a target when source and target are identical, or normalize descriptors 0–2 before pipe construction. Add bounded cases for each initially closed standard descriptor.

### P2 — progressive-disclosure isolation is asserted, not reproduced

The evaluator bundle necessarily contains readable reference code, hidden tests, canonical answers, and reviews. The prose says these are absent from the learner view, but no materialized learner view, allowlist, projection manifest, or transfer-validation result is present. `audit_pack.py` checks path conventions in the full bundle; it does not construct or inspect the artifact a learner receives. In addition, `adversarial/README.md` calls itself evaluator-facing while residing outside a directory named `sealed`, so a filter based only on that name is insufficient.

Keep the evaluator bundle, but add a deterministic student-view projection and validate the projected artifact for forbidden paths/content. Until the harness does that, progressive disclosure and transfer isolation remain inconclusive rather than passed.

### P3 — provenance integrity and generated-material licensing need clearer boundaries

The linked tutorial is conservatively marked `NOASSERTION`, and the pack does not claim its license covers generated content. That is honest. Two reproducibility gaps remain:

- `MANIFEST.yaml` records `provenance_sha256` as `8c9dfc...`, which matches `PROVENANCE.json.snapshot_sha256` but not the provenance file's actual SHA-256 (`2ade2f5c...`). The audit compares selected fields rather than hashing the complete provenance record. If this field intentionally identifies an external snapshot, document that meaning and add a separate digest for the record.
- “Independently generated for personal educational use” is provenance/use context, not an explicit redistribution license for the generated prose, code, and tests. State the intended license or explicitly retain `NOASSERTION` for those artifacts.

The upstream snapshot and tutorial were unavailable here, so the commit, CC0 evidence, and no-copy assertion cannot be promoted beyond internally consistent metadata.

## Positive evidence

- The original candidate remained unchanged; its aggregate file hash was identical before and after review.
- Strict clean builds reproduced for both starter and reference.
- All submitted public and sealed suites passed independently when rerun with outer timeouts.
- The malformed-command side-effect probe confirmed parsing completed before launch.
- The pipe-EOF exercise, review exercise, audit, and benchmark-driver smoke check behaved as documented.
- Validation language is appropriately restrained: `GENERATED`/`PARTIAL`, independent validation required, `productionized: false`, and no fuzz, benchmark, transfer, review, or production label claimed.
- Known lifecycle, job retention, event-loop, terminal, fault-injection, and portability gaps are discussed rather than hidden.

## Disposition

Revise the R4.4 result handling, exact whitespace lexer, and stage-1 test design. Either make closed-standard-descriptor behavior conform or scope it explicitly. Add deterministic student-view validation and clarify provenance-file integrity and generated-content licensing. Retain the conservative manifest labels pending a fresh independent run.
