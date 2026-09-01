# Debugging log

This is a concise engineering record of observable hypotheses, commands,
failures, fixes, and lessons. It does not contain private reasoning traces.

## 2026-08-31 — interpreter mismatch

- **Hypothesis:** the default `python3` could run the new source and tests.
- **Experiment:**
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m unittest discover -s tests -v`
- **Failure:** discovery stopped before behavioral tests. The interpreter was
  Python 3.6 and reported `SyntaxError: future feature annotations is not
  defined` at `from __future__ import annotations`.
- **Follow-up:**
  `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version` reported
  `Python 3.11.5`.
- **Action and lesson:** use the supplied 3.11 interpreter and record its full
  path. Reproducible test commands must name the runtime when `python3` is
  ambiguous.

## 2026-08-31 — boundary fixture initialized too late

- **Hypothesis:** a 50 ms runner timeout with a 35 ms fixture sleep was enough
  for a useful exit-versus-timeout repetition.
- **Experiment:** reran the full suite under Python 3.11.5.
- **Failure:** all eight boundary subtests failed because their PID files did not
  exist. The other tests passed. The timeout included process and interpreter
  startup, so the fixture could be terminated before executing its first write.
- **Change:** first increased the pair to a 300 ms timeout and 250 ms sleep; the
  13-test suite passed. I then made the final test less load-sensitive with a
  500 ms timeout and 420 ms sleep. It still accepts either coherent terminal
  result rather than demanding a particular scheduler outcome.
- **Lesson:** near-boundary tests should exercise classification invariants, not
  encode an assumed startup latency.

## 2026-08-31 — bounded-output and progress check

- **Hypothesis:** selecting both nonblocking pipes while capping only retained
  prefixes prevents deadlock without weakening the space bound.
- **Experiment:** `flood_streams.py` used two threads to write 262,144 bytes to
  stdout and 262,144 bytes to stderr with the runner limit set to 1,024 bytes per
  stream.
- **Result:** the automated check finished, observed both full totals, decoded
  exactly 1,024 retained bytes from each Base64 field, and found both truncation
  flags true.
- **Lesson:** counting, retaining, and draining are separate responsibilities.

## 2026-08-31 — process-tree cleanup check

- **Hypothesis:** new-session group signaling handles descendants, and the grace
  deadline distinguishes cooperative cleanup from escalation.
- **Experiments:** one fixture parent and descendant used normal `SIGTERM`
  behavior; another pair ignored `SIGTERM`. Each wrote two PIDs through its own
  temporary test channel.
- **Result:** both tests returned runner status 11, produced only the
  `timed_out` outcome, and independently found both recorded PIDs gone. Teardown
  retained best-effort `SIGKILL` cleanup even if an assertion were to fail.
- **Lesson:** the report describes policy, while PID checks test the external
  cleanup effect.

## 2026-08-31 — final clean-directory run

- **Experiment:** ran the complete suite from an initially empty temporary
  working directory with Python 3.11.5 and bytecode generation disabled.
- **Result:** 14 tests passed in 8.644 seconds. The full command and combined
  output are preserved in `evidence/TEST_LOG.txt`; runtime and kernel facts are
  in `evidence/ENVIRONMENT.txt`.
- **Cleanup:** the clean test directory was removed after the run. The sleeping
  and process-tree tests' PID disappearance assertions passed.
