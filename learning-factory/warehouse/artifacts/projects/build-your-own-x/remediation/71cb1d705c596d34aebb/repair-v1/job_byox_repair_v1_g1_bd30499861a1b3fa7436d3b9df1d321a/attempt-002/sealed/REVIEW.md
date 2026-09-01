# Sealed implementation review

## Review outcome

The reference is suitable as an executable educational answer for this defined
core. It compiles under the host's strict warning flags and has deterministic
black-box coverage for lexer/parser boundaries, descriptor ordering, concurrent
pipelines, parent and child builtin contexts, process groups, stopped/running
jobs, batch stdin isolation, shutdown, and pseudo-terminal handoff. This review
does not assert production readiness or an independent validation label.

## Positive findings

- Complete physical lines parse before side effects.
- Owned parse structures have uniform partial-failure cleanup.
- Array growth and allocation-size arithmetic are checked.
- Every pipeline stage is forked before foreground waiting.
- Pipe and notification descriptors are closed in child and parent contexts.
- Parent-builtin redirection is transactional and tested on failure.
- Wait statuses stay attached to PIDs; final-stage status is independent of
  completion order.
- The signal handler is limited to an async-signal-safe self-pipe write and
  preserves `errno`.
- Job aggregate state comes from per-process records and IDs are stable.
- Prompt detection and controlling-terminal job control use distinct predicates.
- Timeout-capable Python harnesses put each shell in a disposable session and
  sweep every process group in that session.

## Findings repaired during review

- The original starter could represent only one pipeline despite a list
  grammar; its public types now include a command list, semicolon token, source
  text, runtime hook, separate foreground status, and destruction boundary.
- Batch background commands formerly shared source stdin; stage zero now gets
  `/dev/null` unless an explicit input redirection exists.
- Terminal handoff formerly depended on stdout also being a TTY; it now depends
  on controlling stdin, while the prompt still depends on both streams.
- The controlling terminal was fd 0, which parent redirection could replace; a
  close-on-exec duplicate now carries terminal operations.
- No-argument `exit` formerly used a status overwritten by background launches;
  foreground status is now retained separately.
- Decimal exit parsing previously used bounded `long`; rolling modulo now
  accepts the specified arbitrary-length integer.
- `bg` previously accepted running jobs; it now selects stopped jobs only.
- `ENOTDIR` from command execution now maps to not-found status 127.
- Partial-launch and shutdown cleanup now signal both groups and recorded direct
  PIDs before reaping.
- Auxiliary timeout handlers formerly killed only the shell process group,
  leaving correct pipeline groups alive; they now sweep the disposable session.
- Fresh foreground children formerly could read the controlling terminal before
  `tcsetpgrp`; an explicit launch barrier now releases them only after handoff.
- Stopped pipelines formerly reused an exited final stage's status; they now use
  the rightmost member that is actually stopped.
- Physical stdin lines formerly retained their newline during lexing, letting a
  trailing backslash quote it; both input modes now enforce the same boundary.
- Job IDs with a sign were formerly accepted, and missing shebang interpreters
  were indistinguishable from missing commands; both cases now have explicit
  parsing/location checks and black-box regressions.
- `-c` attached to a terminal formerly inherited the prompt-visible notice flag;
  invocation mode now suppresses optional job notices without disabling
  controlling-terminal job control.
- Descriptor setup formerly exposed raw `EINTR` failures from `SIGCHLD`;
  recoverable pipe, open, duplication, flag, metadata, exec, and terminal
  operations now use explicit retry paths.
- Foreground waiting formerly omitted continued events and could accept a
  stopped aggregate while a continuation was pending. It now requests and
  drains `WCONTINUED` state before returning a stopped result.
- A closed initial fd 0 formerly became the signal-pipe read end and made batch
  input poll forever. Standard descriptors are now reserved before internal
  descriptors are opened, with a bounded closed-stdin regression.

## Residual limitations and risks

- Allocation failure ends the complete shell rather than recovering only the
  current line. Because the fail-fast helpers bypass normal job shutdown, an
  allocation failure while background jobs exist can leave them to the parent
  environment; production code must propagate the error through owned cleanup.
- All pipes are precreated, so extremely long pipelines can hit descriptor
  limits earlier than a rolling launcher. The error path is covered only at
  ordinary host limits, not through systematic syscall injection.
- Child setup diagnostics use libc after `fork`. The program is single-threaded
  and flushes before forking; a future multithreaded version must restrict that
  region to async-signal-safe operations or use `posix_spawn`.
- The shell restores its own terminal modes but does not save a stopped job's
  modes for `fg`.
- A deliberately hostile command can create a new session or double-fork and
  escape the educational job table. This shell is not a containment boundary.
- Unusual `RLIMIT_NOFILE` arrangements beyond initially closed standard
  descriptors do not have dedicated regression cases.
- Pseudo-terminal evidence is from this Linux host. Other POSIX variants may
  differ in `WCONTINUED`, PTY setup, signal numbers, and `execvp` fallback.
- The session-sweep timeout fallback relies on the standard `ps` utility; if it
  is unavailable, cleanup falls back to the session leader's group and is only
  best effort.

## Recommended next tests

Use injected wrappers for `pipe`, `fork`, `open`, `dup2`, `setpgid`, and
`tcsetpgrp`; run long pipelines under a low descriptor limit; test stopped jobs
that alter terminal modes; stress immediate-exit background bursts; add a
sanitizer/fuzzer environment with a working runtime; and run the PTY suite on
at least Linux, macOS, and one BSD. These are productionization inputs, not
claims made by this artifact.
