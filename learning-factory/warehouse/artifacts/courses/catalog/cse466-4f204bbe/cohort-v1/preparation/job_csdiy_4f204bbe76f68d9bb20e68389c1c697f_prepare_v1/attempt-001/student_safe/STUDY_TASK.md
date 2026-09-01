# Study task: build a bounded command runner

## Deliverable

Create a Python 3 program named `safe_run.py` that starts one explicitly supplied local program, supervises it, and writes a bounded JSON execution report. Use only the Python standard library. The implementation is Linux-specific for this unit.

Submit this structure:

```text
safe_run.py
README.md
DESIGN.md
COMPREHENSION_RESPONSES.md
fixtures/
tests/
evidence/
  TEST_LOG.txt
  ENVIRONMENT.txt
```

Do not include copied course challenges, downloaded binaries, secrets, solution write-ups from others, or generated process debris.

## Required command interface

Your program must accept this shape:

```text
python3 safe_run.py \
  --timeout-seconds SECONDS \
  --max-output-bytes BYTES \
  --report PATH \
  -- PROGRAM [ARG ...]
```

`SECONDS` is a positive finite number. `BYTES` is a positive integer and is a separate retained-byte limit for stdout and stderr. `--` ends runner options; every remaining token belongs to the child argument vector. Reject an empty child command or invalid limits with a concise diagnostic.

The runner's own exit codes must be stable:

- `0`: the child exited normally with code 0;
- `10`: the child exited nonzero or was terminated by a signal before the timeout;
- `11`: the timeout policy was activated; and
- `12`: the runner could not start the child or could not produce its required report.

## Behavioral requirements

1. **Exact invocation boundary.** Start the child from an argument vector without invoking or emulating a shell. Preserve empty arguments, whitespace, quotes, wildcard characters, semicolons, dollar signs, and other tokens as literal argument data.

2. **Separate supervision domain.** Start the child in a new process session or process group so timeout cleanup applies to descendants created by a fixture, not to the runner or its caller.

3. **Concurrent pipe handling.** Capture stdout and stderr separately and drain both while the child runs. A child that fills one pipe while writing to the other must not deadlock the runner.

4. **Bounded retention.** Retain at most `BYTES` bytes from each stream in memory and in the report. Continue draining data after that stream reaches its retained-byte limit. Track the total bytes observed for each stream and whether retained data was truncated. Do not first collect unbounded output and truncate it afterward.

5. **Timeout cleanup.** Measure elapsed time with a monotonic clock. At timeout, terminate the child's process group, allow no more than 0.25 seconds for cooperative shutdown, escalate if members remain, and reap the direct child. The runner must finish promptly even when the fixture ignores the first termination request.

6. **Race-aware outcome.** Report one coherent terminal outcome when exit and timeout are close together. Document the rule used to decide whether the timeout policy was activated. Do not claim both a normal exit and a timeout.

7. **Byte-safe capture.** Output can contain arbitrary bytes. Preserve retained data as Base64 rather than assuming it is UTF-8.

8. **Durable report.** Write the report to a temporary file in the destination directory and atomically replace `PATH` only after a complete JSON document is ready. Do not leave a partial destination report after an interrupted or failed write.

## Report contract

The report must be a JSON object with exactly these top-level fields:

```text
schema_version, argv, outcome, exit_code, signal, timed_out,
duration_ms, stdout, stderr, error
```

Use `schema_version: 1`. `argv` is the exact child argument vector. `outcome` is one of `exited`, `signaled`, `timed_out`, or `spawn_error`. `exit_code` and `signal` are either nonnegative integers or `null` as appropriate. `timed_out` is a Boolean. `duration_ms` is a nonnegative integer measured by a monotonic clock. `error` is `null` after a successful spawn and otherwise is an object with string fields `kind` and `message`.

Both `stdout` and `stderr` must be objects with exactly these fields:

```text
bytes_observed, bytes_stored, truncated, data_base64
```

The byte counts are nonnegative integers. `bytes_stored` must equal the decoded length of `data_base64`, must not exceed the configured limit, and must not exceed `bytes_observed`. `truncated` is true exactly when more bytes were observed than stored. A spawn failure still produces a report with empty stream records when the report destination itself is usable.

JSON object-key order and whitespace are not assessed. Do not make tests compare the exact duration or platform-generated error message.

## Harmless fixture and test matrix

Write your own small fixtures under `fixtures/`; do not download test programs. Your automated tests must cover at least:

- a fixture that writes distinct bytes to stdout and stderr and exits 0;
- a fixture that exits with code 7;
- argument round-tripping with an empty token, spaces, `*`, `;`, quotes, and `$` characters, demonstrating that none are interpreted by a shell;
- simultaneous stdout and stderr output exceeding each per-stream limit;
- binary output containing invalid UTF-8 and a zero byte;
- a nonexistent executable and an invalid runner option;
- a child that exceeds the timeout;
- a fixture that starts a sleeping descendant, where both processes respond normally to termination;
- a fixture whose direct child and sleeping descendant ignore the first termination request; and
- at least one near-boundary repetition that checks your documented exit-versus-timeout rule without requiring a particular scheduler outcome.

Every test must have a finite outer deadline. Process-tree tests must record fixture PIDs through a temporary test-only channel, check after the runner returns that the recorded processes are gone, and perform best-effort cleanup in teardown even after an assertion fails.

## Engineering record

In `DESIGN.md`, write 500–900 words covering:

- the states and transitions in your supervision model;
- the invariant that enforces each output bound;
- how stdout and stderr are drained without deadlock;
- the timeout escalation and reaping policy;
- the exit-versus-timeout decision rule;
- atomic report publication; and
- two remaining limitations that are outside this unit.

In `README.md`, give exact run and test commands, supported platform assumptions, exit-code meanings, and a short safety note.

Run the complete test suite from a clean temporary working directory. Save the command and full combined output in `evidence/TEST_LOG.txt`. In `evidence/ENVIRONMENT.txt`, record the UTC test time, Linux kernel identification, Python version, and the exact command used. Evidence is a claim to be independently checked, not proof by itself.

Answer the separate comprehension prompts in `COMPREHENSION_RESPONSES.md`. Keep responses tied to your own implementation and tests.

## Stop condition

Stop after the listed deliverables pass your local test suite and no fixture process remains. Do not attempt catalog challenges or treat this kickoff as course completion.
