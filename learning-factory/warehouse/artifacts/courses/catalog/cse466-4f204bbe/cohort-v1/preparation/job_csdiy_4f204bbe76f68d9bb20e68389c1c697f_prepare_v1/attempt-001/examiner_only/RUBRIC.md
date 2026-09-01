# Independent examiner rubric: Linux process boundaries kickoff

This rubric evaluates only `manager_unit_01_linux_process_boundaries`. It does not evaluate or certify ASU CSE466. Learner claims and saved logs are supporting context; award behavioral credit from examiner-controlled inspection and tests.

## Examiner safety and setup

Use an isolated temporary Linux workspace, Python 3, finite outer timeouts, and harmless examiner-authored fixtures. Disable network access and do not use privileges. Before and after process-tree probes, record fixture PIDs and clean up the exact examiner-created process group. Do not run downloaded binaries or trust learner-provided cleanup scripts as the sole cleanup mechanism.

First preserve the submission and hash the evaluated files. Run the learner's documented tests, then run independent fixtures with different names, timings, output chunk sizes, and byte content. Keep stdout, stderr, reports, exit codes, environment data, and cleanup observations as examiner evidence.

## Critical gates

The submission cannot pass if any of these is observed:

- it invokes a shell, constructs a command string for interpretation, or evaluates child arguments;
- it targets external systems, unrelated processes, privileged interfaces, or other users' data;
- an examiner fixture process remains alive after the runner returns from a timeout test;
- retained output can exceed the configured per-stream bound or is collected without a bound before truncation;
- normal test use can hang without an examiner outer timeout; or
- required reports or evidence are fabricated, materially misleading, or contain secrets.

A critical-gate failure caps the score below 70 even if cleanup succeeds afterward. Deliberately harmful or unauthorized behavior receives no unit credit and must be escalated according to the harness policy.

## Scored criteria (100 points)

### A. Invocation and CLI contract — 15 points

- 6: Independent argument probes preserve empty strings, whitespace, glob characters, semicolons, quotes, and dollar signs exactly, with no shell interpretation.
- 4: Validates required options and produces the specified stable runner exit codes.
- 3: Spawn failure produces a coherent `spawn_error` report when the destination is usable.
- 2: Uses only the standard library and clearly identifies Linux platform assumptions.

### B. Concurrent, bounded, byte-safe output — 20 points

- 7: Independently generated simultaneous stdout/stderr loads complete without pipe deadlock.
- 6: Each retained stream stays within the configured bound during execution; inspection shows no earlier unbounded accumulation.
- 4: Observed/stored counts, truncation flags, and Base64 payloads agree for exact-boundary, over-boundary, empty, zero-byte, and invalid-UTF-8 cases.
- 3: Continues draining after retention stops, allowing the child to make progress and terminate.

### C. Timeout and process-tree lifecycle — 20 points

- 5: Uses a monotonic deadline and returns promptly under examiner outer deadlines.
- 6: Applies initial termination to the new child session/process group and permits at most the specified 0.25-second grace interval.
- 5: Escalates against an ignoring process tree and reaps the direct child.
- 4: Independent PID checks show both responsive and ignoring descendants are gone after return, including repeated runs.

### D. Outcome and report integrity — 15 points

- 5: Produces one coherent outcome with consistent `exit_code`, `signal`, `timed_out`, and runner exit code across normal, nonzero, signaled, timed-out, and spawn-error probes.
- 3: Has a documented, consistently implemented exit-versus-timeout rule.
- 4: Report fields and types match the contract; counts and payloads are internally consistent.
- 3: Publishes a complete report through same-directory temporary-file replacement and handles publication errors without presenting partial JSON as current.

### E. Learner tests and operational evidence — 15 points

- 7: Automated tests cover every required matrix item with meaningful assertions rather than only smoke execution.
- 3: Every test has a finite outer deadline; process fixtures use exact PID observation and teardown cleanup even on assertion failure.
- 3: Tests are isolated, repeatable, do not depend on ordering or network access, and avoid exact timing/error-message assertions.
- 2: `TEST_LOG.txt` and `ENVIRONMENT.txt` contain the requested commands, combined results, UTC time, kernel, and Python version and are consistent with the submission. Independently rerun rather than trusting them.

### F. Design and maintainability — 8 points

- 3: `DESIGN.md` accurately describes states, bounds, concurrency, cleanup, the race rule, atomic publication, and two honest limitations.
- 2: Code separates option parsing, supervision, stream accounting, reporting, and cleanup sufficiently for focused testing.
- 2: Error paths converge on cleanup and do not obscure the primary failure.
- 1: `README.md` provides exact commands, exit meanings, platform scope, and safety boundary.

### G. Comprehension — 7 points

Award credit across all ten responses for accurate reasoning tied to named submission code/tests. Look for these elements collectively:

- mutually exclusive terminal states and an explicit transition/decision point;
- argument data versus shell language;
- pipe-capacity deadlock and concurrent draining;
- `0 <= bytes_stored <= limit`, stored not exceeding observed, decoded length equality, and truncation iff observed exceeds stored;
- separation of bounded retention from continued drainage/progress;
- a plausible deadline/exit race plus a stable policy and scheduler-tolerant test;
- process-group reasoning plus external PID-based cleanup evidence;
- the limited guarantee of atomic replacement;
- a concrete refinement from an abstract algorithmic model to OS behavior; and
- two defensible multi-user hardening needs, without offensive expansion.

Full credit requires concise causal explanations, not merely restating field names. Do not require wording identical to this rubric.

## Decision rule

- **Pass:** at least 80/100, no critical-gate failure, at least 12/20 in section B, and at least 12/20 in section C.
- **Revise:** 60–79, or 80+ with a section-B/section-C minimum missed, provided there is no deliberate safety violation.
- **Not demonstrated:** below 60, non-evaluable submission, or serious safety/authorization breach.

Record the total, each section score, gate results, independent commands, artifact hashes, and evidence locations. A pass may promote only this kickoff unit after validator confirmation; it must not change whole-course completion.
