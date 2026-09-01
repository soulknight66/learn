# Submission: bounded Linux process-boundaries kickoff

## Scope statement

This submission covers only the self-contained kickoff described by the three
learner-safe course files. It does not claim completion of CSE466, an official
ASU or pwn.college module, any catalog challenge, or the wider course.

## Submitted artifacts

- `safe_run.py`: Linux-specific runner using an exact argv boundary, a new child
  session, selector-based dual-pipe draining, bounded retained prefixes,
  monotonic timeout handling, process-group escalation, direct-child reaping,
  Base64 stream data, and same-directory atomic report replacement.
- `fixtures/`: locally written fixtures for separate streams, status 7, exact
  argument capture, concurrent output flooding, arbitrary bytes, sleeping
  execution, process trees, signal exit, and near-deadline repetition.
- `tests/test_safe_run.py`: 14 `unittest` cases with finite outer subprocess
  deadlines, exact report-contract checks, and test-owned PID cleanup.
- `README.md` and `DESIGN.md`: commands, platform and safety assumptions, exit
  meanings, state model, invariants, race policy, publication behavior, and
  remaining limitations.
- `COMPREHENSION_RESPONSES.md`: responses tied to named implementation functions
  and tests.
- `evidence/TEST_LOG.txt` and `evidence/ENVIRONMENT.txt`: the exact clean-working-
  directory command, full combined test output, UTC time, kernel, and Python
  identity.
- `notes.md` and `debugging-log.md`: bounded study notes and an observable record
  of hypotheses, failures, corrections, experiments, and lessons.

## Validation summary

The recorded run used Python 3.11.5 on Linux. All 14 tests passed in 8.644
seconds from an initially empty temporary current directory. Among the checked
behaviors are literal argv round-tripping, 262,144 observed bytes per flooded
stream with only 1,024 stored, invalid-byte capture, spawn failure, invalid
configuration, nonzero and signal exits, direct timeout, cooperative tree
cleanup, forced tree cleanup, atomic replacement, and coherent near-deadline
outcomes. Process tests passed their post-return checks that recorded fixture
PIDs were gone; teardown also contained bounded best-effort cleanup.

These results are recorded evidence for independent validation, not a prose
assertion that the implementation is universally correct. Known out-of-scope
limits include descendants that deliberately escape their process group and the
absence of multi-user sandboxing or general resource isolation.
