# Productionization assessment

Status: not productionized.

Before this design could be considered for routine interactive use, it would need:

- a durable job table keyed by process group, with per-process running/stopped/completed state;
- `jobs`, `fg`, and `bg`, plus terminal-mode save/restore for stopped jobs;
- `SIGHUP` and shell-exit policy for active jobs;
- signal-safe event notification, commonly a self-pipe or signalfd-backed loop;
- deterministic allocation- and syscall-failure injection;
- sanitizer, static-analysis, coverage, fuzz, and long-duration descriptor/zombie testing;
- PTY tests spanning stop/continue, rapid exit during `setpgid`, terminal loss, and nested invocation;
- locale and byte-policy decisions, plus a versioned diagnostics contract if automation consumes errors;
- security documentation making clear that command execution is not isolation.

Expansion, globbing, scripting, and command substitution are product features rather than hardening prerequisites for the stated small-shell scope. If added, each needs its own parse/expand boundary and injection-oriented tests.
