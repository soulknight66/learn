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
