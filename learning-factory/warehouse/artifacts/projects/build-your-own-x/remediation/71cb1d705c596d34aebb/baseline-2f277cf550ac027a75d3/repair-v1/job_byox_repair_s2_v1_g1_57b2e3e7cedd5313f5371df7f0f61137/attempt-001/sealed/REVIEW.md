# Sealed implementation review

Review target: `sealed/reference/src/msh.c` and its black-box contract.

## Confirmed properties

- The complete token stream is validated before the first `fork`.
- Pipe endpoints have explicit child and parent close paths.
- Process creation uses argv-based `execvp`, never a shell string.
- Foreground waits select one process group; asynchronous reaping only mutates
  tracked background jobs.
- Parent built-in descriptors share a restore path.
- PTY exercise coverage checks stop, listing, foreground resume, and Ctrl-C.

## Finding resolved during review

An early `fg` path sent `SIGCONT` before `tcsetpgrp`. A resumed job that read
immediately could receive `SIGTTIN` and stop again. The final implementation
makes terminal transfer the first step inside foreground waiting, then marks
members Running and sends `SIGCONT`.

## Repair generation 1

Independent review exposed additional edge conditions. This revision narrows
unquoted separators to space and tab, treats embedded CR/LF as word bytes,
normalizes inherited `SIGCHLD`, reports an unexpected foreground `ECHILD` as
failure, and validates `exit` and `fg` operands as ASCII digits before
conversion. File and pipe descriptors are moved above 0--2 before wiring, and
redirection closes a source only when it differs from its destination.

The sealed and public PTY harnesses now poll child exit with `WNOHANG` under a
deadline and use TERM/KILL escalation for the shell and observed foreground
groups. Regression tests cover closed standard descriptors, inherited ignored
`SIGCHLD`, byte-exact tokenization, strict numeric operands, and public M5 job
control. Fresh command outcomes are recorded only in `VALIDATION.md`.

## Accepted limitations

- Allocation exhaustion exits immediately rather than unwinding.
- Interactive terminal modes (`termios`) are not snapshotted per stopped job.
- Background jobs are not hung up, adopted, or synchronously drained at shell
  exit.
- Diagnostics are stable in category but not localized or byte-perfect across
  operating systems because `strerror` text is host supplied.
- The 1 MiB limit is checked after `getline` has allocated the line.

These limitations are consistent with the scoped educational contract but
block a claim of production readiness. `MANIFEST.yaml` therefore remains
`productionized: false` with `GENERATED` and `PARTIAL` labels only.
