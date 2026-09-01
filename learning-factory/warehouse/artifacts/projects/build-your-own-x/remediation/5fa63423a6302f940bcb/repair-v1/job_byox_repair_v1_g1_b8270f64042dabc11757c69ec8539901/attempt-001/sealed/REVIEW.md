# Reference implementation review

This review is a design-level audit guide, not an independent validation label.
It records what a reviewer should establish from code and tests before trusting
the reference.

## Highest-risk paths

### Descriptor lifetime

For an N-stage pipeline, enumerate every pipe descriptor in the parent and in
each child. After `dup2`, a child should close both original endpoints, including
the descriptor that was duplicated. The parent should close endpoints as soon
as it no longer needs them. One stray write endpoint explains the classic
pipeline that produces all expected bytes and then never reaches EOF.

Audit parent-builtin redirection separately. Every applied descriptor must have
a saved original, and restoration must occur after failures as well as success.
Buffered output must be flushed on the correct side of each `dup2` boundary.

### Partial launch cleanup

Force the second or later `pipe`, `fork`, `open`, and `setpgid` operation to
fail. Confirm that already-created children are not abandoned, no descriptor is
leaked, terminal ownership returns to the shell, and no incomplete job appears
healthy. Cleanup code needs the count of resources actually acquired, not the
count the parser requested.

### Signal and job-table races

Look for the exact mask boundary around fork, process-group setup, and job-table
publication. A child that exits immediately must still be attributable when it
is reaped. The child must restore the old signal mask, and inherited ignored
interactive signals must be reset before builtin or external execution.

The handler should be auditable at a glance: save/restore `errno` if needed and
perform only async-signal-safe flagging. Formatted output, allocation, table
compaction, and job-state derivation belong outside it.

### Terminal ownership

Every successful foreground handoff must pair with a reclaim, including stopped
jobs, wait errors, failed `SIGCONT`, and builtin error paths. Test from a real
pseudo-terminal: pipes used by a test runner do not exercise `tcsetpgrp`,
`SIGTTIN`, or terminal-generated Ctrl-C/Ctrl-Z behavior.

### Parser ownership and bounds

Verify that explicit empty words survive, token fragments concatenate, operator
characters lose special meaning when quoted/escaped, and all output buffers are
NUL-terminated. Every growable append must check addition, multiplication, and
allocation before publishing a pointer/count change. Error returns must leave
the output structure safe to discard and must not launch a prefix of the input.

### Wait-status interpretation

No raw wait status should escape as a command status. Code must distinguish
normal exit, signal termination, stop, and continuation before accessing the
corresponding macros. Pipeline completion should reflect a documented stage
policy and should wait for all members, not merely the process-group leader.

## Security and robustness observations

- Passing an argv vector to a non-fallback execution primitive avoids an extra
  command-string interpretation layer. Manual `PATH` search must stop and
  diagnose ENOEXEC rather than permitting libc to invoke a host shell. No code
  should reassemble parsed words and invoke `/bin/sh -c`.
- User text used in diagnostics must be passed through `%s` or equivalent, not
  used as the format string.
- File opens need deliberate flags and modes: `>` truncates, `>>` appends, and
  neither should accidentally inherit an unrelated descriptor into `exec`.
- Fixed capacities reduce allocator complexity but do not help unless every
  boundary is checked before arithmetic and copying.
- Children should call `_exit`, not `exit`, after post-fork setup failure.
- External lookup intentionally trusts the caller's `PATH`. This is shell
  behavior, but it is inappropriate for a privileged service.
- The project has no authorization boundary, sandbox, resource quota, or
  hostile multi-user isolation. It must not execute untrusted commands as a
  privileged account.

## Review questions tied to tests

1. Does `printf '%s' ""` receive a real empty argument rather than no argument?
2. Does `printf x|cat>/dev/null` tokenize correctly without spaces?
3. Does a syntax error after a valid-looking prefix create no file and launch no
   process?
4. Does `printf x > first > second` fail during parsing without creating or
   truncating either file?
5. Does `pwd > out` restore the shell's stdout before the next prompt or
   command?
6. Does a long-output producer piped to an early-exiting consumer terminate
   without the shell hanging?
7. Can an immediate background exit be reaped and removed without a permanent
   RUNNING entry?
8. Does Ctrl-C affect the foreground process group while leaving the shell
   usable?
9. Does Ctrl-Z produce one stopped pipeline job that `bg` and `fg` can resume?
10. Can repeated background jobs run past PID reuse without statuses being
    assigned solely by stale PID data?
11. Does a quick background child get reaped while an unrelated, synchronized
    foreground fixture remains alive?
12. Does an executable text file without an interpreter header fail with 126
    without any of its contents being interpreted?

## Known scope limitations

Even if all project tests pass, the reference remains a teaching shell. It has
no operational input/resource quota, a deliberately incomplete language, no
line editor or history, limited diagnostics, no persistent job specification
language, and no cross-platform backend. Test completion does not establish POSIX shell
conformance, security isolation, production readiness, or suitability as a
login shell.

## Validation posture

The appropriate evidence is layered: compiler warnings and sanitizers for
memory/descriptor mistakes, deterministic batch tests for parsing and status,
pseudo-terminal integration tests for job control, fault injection for partial
launch, and repeated stress tests for timing races. Results belong in the
validation record only after commands are actually run by the responsible
harness. This document intentionally makes no claim that those checks passed.
