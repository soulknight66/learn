# Productionization assessment

`byosh` is not productionized. It is a scope-limited educational shell and carries
the repository's `GENERATED`/`PARTIAL` posture until independent validation
records stronger evidence. Building or passing a local test suite would not by
itself make it safe as a login shell, privileged command runner, or untrusted
execution service.

## Required engineering before broader use

### Define the product boundary

Choose whether this is an interactive user shell, an embedded command runner,
or a script interpreter. Those products need different compatibility,
security, and recovery contracts. Publish the grammar, exit-status policy,
limits, supported operating systems, and terminal assumptions as versioned
interfaces.

### Introduce operational resource limits

Dynamic storage avoids arbitrary parser constants but does not bound resource
consumption. Add configurable, observable ceilings for input bytes, word and
argument bytes, concurrent jobs, processes per pipeline, open descriptors, and
retained completed jobs. Limit failures must remain atomic and name the
exceeded resource. A fixed-capacity build can expose the same policy rather
than silently clipping.

### Harden lifecycle failure paths

Systematically inject failures into allocation, `pipe`, `open`, `fork`,
`setpgid`, `tcsetpgrp`, `dup2`, `exec`, `waitpid`, and output. Establish a
shutdown protocol that signals entire owned process groups, allows a bounded
grace period, escalates if needed, and reaps every child. Decide what happens
when terminal ownership cannot be recovered.

### Generalize the event loop

The teaching reference integrates line input and child notifications with a
minimal self-pipe/`pselect` loop. A broader product must extend or replace it
with a documented backend for terminal resize, shutdown, timers, and UI input,
with explicit ordering for prompt rendering and background notifications.
Preserve the reference's atomic signal-mask boundary; do not rely on library
calls being transparently restarted.

### Expand terminal testing

Run automated pseudo-terminal scenarios for Ctrl-C, Ctrl-Z, EOF, rapid stop/
continue/exit, background terminal reads, shell suspension, and terminal loss.
Repeat under multiple supported kernels/libcs and under slow, heavily loaded
schedulers. Batch-only tests cannot validate job control.

### Security model

Never install the program setuid or run untrusted input with ambient privilege.
For a service, isolate commands in a separately supervised sandbox with an
explicit environment, working directory, identity, descriptor allowlist,
resource limits, and filesystem/network policy. Avoid inheriting secrets or
service descriptors. Decide whether `PATH` lookup is allowed; privileged
launchers should generally resolve an allowlisted executable instead.

### Language compatibility and fuzzing

If compatibility is a goal, select a published shell standard and create a
conformance matrix. Otherwise keep the language explicitly non-POSIX. Fuzz the
lexer/parser with sanitizers, include arbitrary bytes allowed by the input
contract, and assert that syntax failure has no side effects. Add model-based
tests for descriptor graphs and job-state transitions.

### Observability without leakage

Use structured diagnostic categories for parse, redirection, launch, exec,
wait, and terminal failures. Record aggregate counts and latency only when
enabled; do not log command text, arguments, environments, or paths by default,
because they frequently contain secrets. Make job identifiers distinct from
recycled PIDs.

### Release discipline

Adopt reproducible builds, warning-clean supported compilers, ASan/UBSan and
race-focused CI, dependency/toolchain inventories, signed release artifacts,
and upgrade/rollback procedures. Independent reviewers should validate the
threat model and job-control behavior before any readiness label changes.

## Suggested evidence gates

1. **Functional:** deterministic parser, redirection, builtin, status, and
   pipeline tests pass on all supported targets.
2. **Interactive:** pseudo-terminal job-control tests pass repeatedly without
   hangs or leaked children.
3. **Robustness:** fault-injection and sanitizer runs cover partial ownership and
   cleanup paths.
4. **Security:** a documented privilege/environment/descriptor review and
   hostile-input fuzz campaign find no unresolved high-severity issue.
5. **Operations:** bounded shutdown, metrics, packaging, and rollback are
   exercised in the intended deployment environment.

These are proposed gates, not recorded results. Promotion remains the job of an
independent validator.
