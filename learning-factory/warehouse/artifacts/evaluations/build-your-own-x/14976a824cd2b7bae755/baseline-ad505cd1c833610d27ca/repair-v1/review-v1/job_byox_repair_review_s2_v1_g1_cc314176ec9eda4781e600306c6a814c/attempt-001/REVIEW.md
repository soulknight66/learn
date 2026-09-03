# Independent review

Verdict: **PASS**, advisory only. No blocking correctness or honesty defect was found for an artifact
that deliberately remains `GENERATED` + `PARTIAL`. This review does not publish `REVIEWED` or any
other validation label; only the orchestrator-controlled acceptance validator may do that.

## Prioritized findings

### P0/P1 — none

The reference controller and runner conform to the stated educational contract in the paths and
states inspected. The validation record avoids promotion language, accurately distinguishes test
doubles from namespace execution, and disclaims production safety.

### P2 — source provenance remains an external promotion gate

The IDs and commit agree across the manifest and provenance object, and the license boundary clearly
separates the CC0 catalog/generated material from the linked resource whose license is
`NOASSERTION`. The immutable catalog baseline itself is not in this workspace: its path is the
placeholder `<immutable-byox-baseline>` and its upstream URL is null. Consequently, the claimed
snapshot, source line, originality, and linked-resource license could not be re-derived here. This is
consistent with `independent_validation=REQUIRED` and is not a reason to reject the current partial
artifact, but it remains a gate for any stronger provenance or transfer claim.

### P2 — learner-view exclusion was not transfer-verified

The full reviewer pack necessarily contains sealed implementations, tests, and answers. Structural
inspection found no sealed/reference directory nested under `starter/`, `public_tests/`, or
`environment/`, and the public material does not directly reveal the solution. No separately
materialized learner view was supplied, however. A publisher must continue to exclude all `sealed/`
content rather than expose this full pack to learners. The candidate makes no `TRANSFER_VERIFIED`
claim, so this is an accurately disclosed promotion limitation.

### P3 — document the provenance digest semantics when exporting the pack

`MANIFEST.yaml.provenance_sha256` equals `PROVENANCE.json.snapshot_sha256`
(`9c1c2b...68c95d`), not the raw or canonical digest of the accompanying provenance file
(`6c6ad5...064768` and `7b2dac...b2426`). The candidate verifier separately pins the canonical
object, so the submitted objects are internally consistent. The field relationship is not explained
outside that verifier; documenting it would make standalone verification less ambiguous.

## Correctness and reproducibility

- All shell sources passed `bash -n` under GNU Bash 4.4.20.
- Re-execution produced 8/8 public, 9/9 sealed lifecycle, and 6/6 adversarial passes. The intentionally
  incomplete starter produced the disclosed 7/8 failures and exit 1.
- A separately authored controller probe used system `printf` and `false` as runners. It confirmed
  unusual argv boundaries, exact runner statuses, deterministic listing, traversal rejection, and a
  scoped delete without depending on the candidate test scripts.
- A separately authored C probe built with the configured GCC 15.2.0 ran through the reference
  namespace runner as PID 1 and mapped UID 0, with isolated hostname, `/` cwd, readable private
  `/proc`, and intact whitespace, glob, semicolon, and empty arguments.
- The candidate's environment and real-runner probes both completed. These are one-host availability
  observations, not containment or portability evidence.
- Strict JSON parsing rejected duplicate/nonstandard constructs; project ID, source ID, and source
  commit match across the manifest and provenance object. The reported raw hashes reproduced.

The candidate is read-only in this review workspace, so its builder commands that choose a
candidate-local `TMPDIR` cannot be repeated literally here. The tests were run with the writable
parent workspace as `TMPDIR`; they create unique directories and remove them on exit.

## Progressive disclosure and learner usefulness

The learning path is strong: a normative requirements document, concise concept explanations,
design questions, milestone-oriented starter files, a visible contract suite, focused debugging and
review exercises, and sealed explanations all reinforce one another. The public suite is explicitly
described as incomplete, and the starter visibly fails instead of creating a misleading green
baseline. Safety-sensitive ideas—validated names, exact deletion scope, inert metadata, argv arrays,
atomic publication, lifecycle locks, and namespace limitations—are presented at useful points in the
progression.

The scope is also honest. Full copies and directory locks are framed as teaching choices, while
crash recovery, cgroups, networking, capability reduction, seccomp, image verification, supervision,
and hostile multi-user safety are explicitly out of scope.

## License, provenance, and validation honesty

`LICENSE_BOUNDARY.md` states a coherent CC0 boundary for generated material, does not infer a license
for the linked tutorial, and denies copying or fetching that tutorial. The latter historical claims
cannot be proven from this workspace and are therefore retained as limitations rather than accepted
facts.

The builder's `VALIDATION.md` is unusually careful about evidentiary boundaries. Every material
command result checked here reproduced, including the host identity warnings, exact suite totals,
real-runner output, file hashes, and expected starter failure. It claims neither fuzzing nor a
benchmark, transfer verification, portability, security certification, or production readiness.

## Residual limitations

ShellCheck, `rg`, and `git` were unavailable. The configured GCC worked, but static libc was absent,
so the independent namespace probe used a dynamically linked binary with copied dependencies. This
review did not perform fuzzing, fault injection, long-duration contention, resource-exhaustion tests,
a kernel/filesystem matrix, hostile-workload containment analysis, benchmarking, or learner-view
transfer validation.
