# Productionization assessment

The artifact is **not productionized**. The reference is an educational POSIX
shell with a deliberately small language, not a secure or compatible command
interpreter. No local test run changes that status.

## Gaps that block production use

- The grammar omits expansions, assignments, here-documents, compound syntax,
  subshells, functions, and the compatibility rules users expect from a shell.
- Diagnostics are not localized and do not carry complete source spans.
- Resource ceilings for line length, arguments, jobs, and pipeline width need a
  documented policy and tests.
- Allocation-failure paths and every syscall fault require injected-failure
  coverage.
- Interactive behavior needs a multi-platform pseudo-terminal matrix and
  sustained race testing around stop/continue/exit transitions.
- The security model is intentionally the caller's authority. This must never
  be presented as a sandbox for untrusted commands.
- Portability work is needed for macOS and BSD variants; native Windows would
  require a different process/terminal layer.
- Fuzzing, sanitizers, descriptor-leak checking, static analysis, and long-run
  process accounting require independent evidence not present in the manifest.

## A credible hardening sequence

1. Freeze a grammar and compatibility target, then attach source spans to every
   token and AST diagnostic.
2. Put OS operations behind a narrow interface so failures can be injected
   deterministically, including partial pipeline construction.
3. Track every member of every process group explicitly and assert legal job
   state transitions.
4. Retain or replace the current self-pipe event source deliberately, and audit
   all signal-mask and notification-overflow boundaries.
5. Add configurable limits and guarantee cleanup on every limit or syscall
   failure.
6. Run parser fuzzing, pseudo-terminal race tests, sanitizer builds, static
   analysis, descriptor/process leak tests, and platform CI.
7. Threat-model privileged invocation, environment inheritance, PATH lookup,
   startup files, and file-descriptor inheritance. Refuse elevated execution
   unless a separately reviewed policy demands it.
8. Produce an operator manual and compatibility statement, then obtain an
   independent security and portability review.

## Release gates

A production claim would require reproducible builds, a supported-platform
matrix, zero known high-severity findings, fuzzing duration and corpus evidence,
terminal stress evidence, explicit ownership and maintenance, and a documented
vulnerability response process. None is asserted here.
