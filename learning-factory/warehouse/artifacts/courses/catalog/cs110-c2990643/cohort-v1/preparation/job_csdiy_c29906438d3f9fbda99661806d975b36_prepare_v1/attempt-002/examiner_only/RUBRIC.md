# Independent Rubric — Reliable POSIX Process Supervision

This document is examiner-only. Evaluate the submitted artifacts and observed behavior; do not accept a learner's prose claim as evidence that code ran. The kickoff is worth 100 points and can establish completion of this unit only. It cannot establish completion of CS110.

Use a POSIX test environment, a fresh temporary directory, and bounded test-process timeouts. Run `make -C submission clean all` and `make -C submission test` before manual inspection. Preserve command output for any failed category.

## Scoring

### Build and public contract — 10 points

- 4: clean build produces `submission/build/proc-run` with no third-party dependency.
- 3: required syntax is parsed; malformed or incomplete options fail with status 125 before a child is launched.
- 3: README accurately documents platform, commands, syntax, result codes, debugging observation, and limitations.

### Direct execution and argument integrity — 15 points

- 6: implementation uses `fork` plus an `exec`-family call with an argument vector and has no `system`, `popen`, or shell intermediary.
- 5: black-box helpers observe exact preservation of empty arguments, embedded spaces, quotes, wildcard characters, semicolons, and dollar signs; no shell expansion or side effect occurs.
- 4: nonexistent-program execution returns 127, emits a useful diagnostic, and cannot fall through into parent logic.

### Descriptor and failure-path discipline — 15 points

- 6: child stdout and stderr are created/truncated and remain separate; runner diagnostics remain on the runner stderr.
- 5: descriptor ownership and closure are correct in parent and child, including partial setup failure.
- 4: failures are checked and reported without false success; interruption handling is deliberate and bounded.

### Lifecycle and status handling — 20 points

- 7: normal statuses, including a nonzero status, are propagated as specified.
- 5: signal termination is detected with the wait-status macros and mapped to `128 + signal_number`.
- 5: every successfully forked direct child is reaped exactly once along success, failure, and timeout paths; repeated runs do not hang or leave a direct-child zombie while the runner lives.
- 3: parent and child control paths are clearly separated, and the child uses a safe immediate-exit path after post-fork failure.

### Timeout and process-group control — 20 points

- 5: deadline is based on a monotonic clock and wait/poll work is bounded.
- 5: the child is established as a new process-group leader with race-aware handling in both sides or an equivalently justified robust technique.
- 6: timeout sends SIGTERM to the group, provides approximately 200 ms of bounded grace, escalates to SIGKILL when needed, reaps the direct child, and returns 124.
- 4: an examiner helper that forks a descendant cannot write a delayed marker after timeout; naturally exiting near-deadline children do not cause an indefinite wait or double reap.

### Automated evidence — 10 points

- 6: `make test` automatically covers every case named in the learner task and exits nonzero on a failed assertion.
- 2: tests use isolated temporary paths, bounded waits, and cleanup that does not target unrelated processes.
- 2: tests avoid fragile exact timing and are repeatable for five consecutive runs under moderate load.

### Design reasoning and comprehension — 10 points

- 4: DESIGN describes states, descriptor ownership, at least four true lifecycle invariants, significant failure points, and justified interface boundaries consistent with the code.
- 6: comprehension responses correctly address the indicators below and cite implementation evidence where requested.

## Comprehension answer indicators

Award up to 0.6 point per response. A correct response should contain the following substance; equivalent precise reasoning earns credit.

1. Memory mappings are logically copied with copy-on-write semantics, while inherited descriptors refer to shared open-file descriptions and offsets; closing or duplicating descriptor-table entries has per-process effects, while writes/offset changes affect the shared underlying object.
2. `exec` receives already separated strings and performs no shell grammar, expansion, substitution, or metacharacter execution. The example must actually distinguish literal argv from shell interpretation.
3. It distinguishes ordinary exit (`WIFEXITED`/`WEXITSTATUS`), signal death (`WIFSIGNALED`/`WTERMSIG`), and possibly stopped/continued reports only if requested; launch failure and timeout are runner policy outcomes built around child status, not raw status integers.
4. The post-fork child reports the setup/exec error through its redirected stderr or a deliberate error channel, then calls an immediate-exit primitive; the parent waits, interprets the result, and exits without executing the child branch.
5. A monotonic clock measures elapsed duration and is unaffected by wall-clock corrections such as NTP adjustment or administrative/calendar changes.
6. The child can exit just before or during a timeout decision. Signal failure due to an already absent target can be benign, but the parent must reach exactly one successful reap and one final result without hanging or reaping twice.
7. Group signaling reaches descendants that stay in the group; it does not reach escaped/re-grouped processes and alone does not provide namespaces, resource limits, or a security boundary.
8. The response names a real interruptible call, distinguishes `EINTR` from other errors, and ties retry behavior to current deadline/lifecycle state rather than retrying blindly.
9. A timeout-boundary test is the usual candidate. Sound answers use generous relative margins, bounded outer waits, observable eventual effects, and no exact scheduler timing assumption.
10. Plausible choices include structured result reporting, stable error channels, output-size controls, cancellation semantics, resource limits, security isolation, unique job identity, metrics, or descendant accounting. Each needs a concrete compatibility, complexity, reliability, or observability tradeoff.

## Caps and non-credit conditions

- Cap the total at 55 if child commands are launched through a shell or a command string, because the central argument-boundary objective is absent.
- Cap the total at 60 if the runner can wait indefinitely after its configured deadline or fails to reap a successfully forked direct child on an exercised path.
- Cap the total at 70 if timeout only targets the direct child and an exercised same-group descendant survives.
- Give no points for an automated behavior that is asserted only in prose or a skipped/disabled test.
- Do not deduct merely for a different internal architecture when black-box behavior, lifecycle invariants, and POSIX reasoning are correct.

To mark this kickoff unit complete, require at least 80/100, no applicable cap below 80, successful clean build, and passing examiner checks for literal argv preservation, separate output, normal/nonzero status, launch failure, group timeout, bounded completion, and direct-child reap. Record the result as kickoff-unit evidence only.
