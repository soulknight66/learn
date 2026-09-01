# Debugging log

## Scope and initial hypothesis

Only the weighted-interval kickoff component was attempted. The central
hypothesis was that the reverse-bit tie contract can be implemented locally in
prefix DP: include the newest canonical job only on a strict value improvement;
exclude it on equality. Direct tie examples and an exhaustive oracle were
chosen to try to falsify this hypothesis.

## Experiments

1. **First clean-process test attempt**

   Command: `PYTHONPATH=submission python3 -m unittest -v submission/test_interval_scheduler.py`

   Result: failed before collecting the suite with
   `ModuleNotFoundError: No module named 'dataclasses'`.

   Diagnosis: the unqualified executable was `/usr/bin/python3`, version 3.6.8.
   The required public API itself uses the standard-library `dataclass`, and the
   workspace provides Python 3.11.5 separately. This was an interpreter/tooling
   mismatch, not a scheduler discrepancy. I did not weaken the API or add a
   third-party backport.

2. **Interpreter check**

   `python3 --version` reported 3.6.8. The provided executable
   `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3` was present.

3. **Clean rerun with the provided toolchain selected**

   Command:
   `PATH=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin:$PATH PYTHONPATH=submission python3 -m unittest -v submission/test_interval_scheduler.py`

   Result: all 16 tests passed in 0.081 seconds. The run included all six input
   permutations of the explicit `A,B,C` tie and 240 fixed-seed generated cases
   compared with the exhaustive subset oracle. No production/oracle discrepancy
   occurred.

4. **Final artifact audit and rerun**

   The `submission/` directory contained exactly the four required learner
   artifacts, `DESIGN.md` was 997 words (within the requested range), and the
   same Python 3.11 test command again passed all 16 tests in 0.081 seconds.

## Lessons retained

- A reproducible command still needs a supported interpreter selected; the
  language-level API requirements should be checked before diagnosing source.
- Testing only optimum totals would conceal canonical tie bugs. Differential
  evidence must compare the returned ordered IDs.
- The global-looking tie rule becomes a local equality decision only because
  DP processes canonical prefixes and the current job is their greatest index;
  that connection belongs in both the proof and reconstruction design.
