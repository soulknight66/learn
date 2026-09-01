# Examiner feedback

Result: **REVISE**. The submission cannot be promoted on the available evidence.

The central problem is packaging and verifiability, not an obvious probability misconception. `SUBMISSION.md` points to a complete `submission/` tree, but that directory is absent. Consequently, there is no source, test suite, README, report, comprehension response, or experiment JSON to inspect.

I ran the documented test shape with a 30-second bound:

```text
env PYTHONPATH=submission/src python3 -m unittest discover -s submission/tests -v
```

It exited 1 immediately on Python 3.6.8 because `submission/tests` does not exist. A full file search also found no JSON records. The statements that 12 tests passed and six experiments completed may describe earlier local work, but they are not independently checkable in this workspace.

Score record: A=1, B=3, C=2, D=0, E=3, F=1.5; total 10.5/100. The missing-files and non-running-submission gates apply regardless of that score. This is an examiner label only; the harness-controlled validator makes the durable job-state decision.

The visible notes do show useful engineering judgment: they distinguish replay from correctness, recognize floating-point endpoint behavior, account for interpreter compatibility, avoid global RNG coupling in the intended design, and describe the old-or-new visibility property and limitations of temporary-write plus replacement. No implementation credit can be based on those prose claims alone.

For the next attempt:

1. Add the complete `submission/` tree listed in `SUBMISSION.md`, including source, tests, README, report, comprehension answers, and all six JSON records.
2. Re-run the documented command from a clean copy using the default offline interpreter, and retain its actual exit status and captured output.
3. Parse every committed result record and check its schema, types, domains, counts, probability ranges, parameters, seed, trial count, model identity, and interval label.
4. Ensure deterministic tests exercise the advertised boundaries, invalid inputs, RNG isolation/replay, independent oracle, JSON contract, and CLI success and failure behavior.
5. Make artifact paths and filename casing in `SUBMISSION.md` match the files that are actually delivered.

Preserve the current failure evidence rather than replacing it; a later complete attempt can demonstrate that the transfer gap has been closed.
