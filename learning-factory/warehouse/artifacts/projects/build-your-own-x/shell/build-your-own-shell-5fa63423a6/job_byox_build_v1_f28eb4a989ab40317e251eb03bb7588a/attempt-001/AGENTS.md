# Learner Agent Guide

This repository is a learning exercise: help the learner build and reason about the shell, but do not
replace the exercise with an imported implementation. Treat [REQUIREMENTS.md](REQUIREMENTS.md) as the
behavioral contract and keep implementation work in `starter/`.

## Working agreement

- Begin by inspecting the scaffold, its TODO markers, and the public tests. Do not assume a function or
  module exists because a conventional shell uses one.
- Preserve the public command-line interface: the built program is `starter/byosh` and accepts either
  no arguments or `-c COMMAND`.
- Make one milestone-sized change at a time. Separate lexing, parsing, process execution, job tracking,
  and presentation so each can be tested independently.
- Prefer small, deterministic tests over interactive anecdotes. For terminal behavior, use a
  pseudo-terminal with explicit timeouts.
- Never invoke a subprocess through a host shell merely to implement the assignment. Launch the
  requested program through the process APIs you are learning.
- Do not copy an existing shell or tutorial implementation. External documentation may clarify an OS
  interface, but the design and code here should be independently reasoned and attributable.
- Do not broaden the grammar until all required cases pass. Record optional extensions distinctly.

## Before editing

1. Identify the current milestone and the smallest observable behavior that is missing.
2. Read only the corresponding requirements and concept notes.
3. Write down ownership: which component allocates a token, command, job, descriptor, or process
   record, and which component releases it.
4. Add or identify a test that fails for the intended reason.

Ask the learner before changing a public interface, build command, or required behavior. If the
scaffold and requirements appear inconsistent, report the exact conflict rather than quietly choosing
one.

## While editing

- Compile as C using the flags supplied by the scaffold. Fix warnings; do not suppress them broadly.
- Check every allocation and OS call that can fail. Preserve the first useful error while still
  performing cleanup.
- Keep signal handlers minimal and limited to operations permitted in that context. Do normal job-table
  work in the main flow.
- Treat file descriptors as owned resources. After creating or duplicating one, state which process
  needs it and close every other copy.
- Treat child status as event data, not as a boolean. A process may exit, be signaled, stop, or continue.
- Block or otherwise coordinate child-state notifications while performing job-table updates so rapid
  children cannot expose a half-created job.
- Do not add sleeps to make races disappear. Synchronize the state transition or make the test wait for
  an observable event.
- Keep diagnostics on standard error and command output on standard output.

## Verification by milestone

Run a clean build plus the narrowest relevant test after each edit. Before claiming a milestone is
complete, cover at least:

- normal input and malformed input;
- success and one forced failure path;
- repeated execution in the same shell process;
- cleanup after partial construction;
- a bounded-time test for any behavior that could hang.

For pipelines, use enough data to reveal sequential-start deadlocks. For job control, test through a
pseudo-terminal rather than a plain pipe. Never leave an interactive child or stopped process behind
after a test.

## Handoff

Report what behavior changed, which files changed, the exact commands run, and their observed result.
Call out tests that were not run and explain why. A build completing successfully is evidence only for
the build; it is not evidence that parsing, descriptor ownership, or job control is correct.
