# Revision debugging log

Provenance: commands and observations below are from this bounded workspace.
Validation label: **ACTUAL LOCAL RUNS**, except where a result is explicitly
identified as the prior examiner's published observation.

Shell startup repeatedly printed unresolved numeric user/group-name warnings.
They were retained in captured tool output but did not change Python exit codes.

## 1. Inventory and externally observed failure

The first scoped listing command was:

```bash
rg --files ASSIGNMENT PRIOR_ATTEMPT EXAMINER_FEEDBACK student_work 2>/dev/null
```

It produced no file paths, so it was inconclusive. I followed with a shallow,
explicit listing of only the supplied areas:

```bash
pwd
ls -la
find ASSIGNMENT PRIOR_ATTEMPT EXAMINER_FEEDBACK student_work -maxdepth 2 -type f -print 2>/dev/null
```

Observation: the three read-only input directories were present and
`student_work/` was absent. The examiner's published evidence separately stated
that the prior staged copy lacked `lease_queue.py`, `test_lease_queue.py`,
`DESIGN.md`, and `INCIDENT.md`; its clean harness exited 1 with
`ModuleNotFoundError: No module named 'test_lease_queue'`. I did not reinterpret
that prose as implementation evidence. Revision: create and preserve the four
missing artifacts, then rerun the same import condition.

## 2. Interpreter and compile check

Command:

```bash
python3 --version
command -v python3
```

Observation:

```text
Python 3.6.8
/usr/bin/python3
```

I chose immutable `typing.NamedTuple` values and Python-3.6-compatible
annotations. After writing the model, I ran:

```bash
PYTHONPATH=student_work python3 -m py_compile student_work/lease_queue.py
```

Observation: exit 0 with no Python diagnostic. There was no compile failure in
this revision.

## 3. First full revision test run

Working directory: `student_work/`.

```bash
python3 -m unittest -v test_lease_queue.py
```

Observed summary:

```text
Ran 17 tests in 0.003s

OK
```

All six `ParcelQPublicTraceTests`, seven `ParcelQContractTests`, and four
`UnsafeExcerptIncidentTests` reported `ok`; none was skipped. There were no red
tests to conceal or revise in this run.

## 4. Focused unsafe-excerpt experiments

Command:

```bash
python3 -m unittest -v test_lease_queue.UnsafeExcerptIncidentTests
```

Observed summary:

```text
Ran 4 tests in 0.000s

OK
```

Here `OK` means all four defect reproducers observed their expected unsafe
outcome: mutation before a stale rejection, mutation before an ID replay,
higher-epoch self-authorization, and inconsistent expiry handling. The
hypothesis cycles and safe-model revisions are preserved in `INCIDENT.md`.

I also ran a focused logical trace with grants at ticks 0 and 3 and old-owner
delivery at tick 4. Its selected JSON showed active epoch 2, presented epoch 1,
decision `FENCED`, `READY` before and after, `state_changed: false`, and
`history_changed: false`. The exact records are in `INCIDENT.md`.

## 5. Fresh-copy reproduction of the examiner condition

From the attempt root, I created a temporary directory inside the writable
workspace:

```bash
mktemp -d ./.revision-cleancheck.XXXXXX
```

The final check returned `./.revision-finalcheck.B9OoFN`. I copied the complete
submitted set, including the four core deliverables:

```bash
cp student_work/lease_queue.py student_work/test_lease_queue.py student_work/DESIGN.md student_work/INCIDENT.md student_work/notes.md student_work/submission.md student_work/debugging-log.md student_work/self-check.md .revision-finalcheck.B9OoFN/
```

With `.revision-finalcheck.B9OoFN` as the working directory, I ran:

```bash
env -u PYTHONPATH python3 -B -m unittest -v test_lease_queue.py
```

Observed summary and status:

```text
Ran 17 tests in 0.003s

OK
```

The process exited 0. `-B` prevented bytecode artifacts from supplying an
accidental import path. I then explicitly removed only that temporary clean-copy
directory; the submitted sources remained in `student_work/`.

## Current status and remaining diagnostics

No known local test is red. This does not resolve the prior failure until an
independent orchestrator stages and validates this revision. The model also
leaves real clocks, concurrent processes, persistent recovery, coordinator
failover, replication, networks, and hostile credentials out of scope.

If the bounded exercise were extended under separate authorization, the next
diagnostic would enumerate short grant/delivery traces and check invariants
against each prefix, followed by crash-consistency and concurrent-process tests
for a genuinely durable implementation. Neither extension nor transfer
verification was attempted here.
