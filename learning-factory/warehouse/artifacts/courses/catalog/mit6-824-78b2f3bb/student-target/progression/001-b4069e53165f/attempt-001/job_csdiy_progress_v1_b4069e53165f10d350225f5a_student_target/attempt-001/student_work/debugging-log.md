# Debugging log

Provenance: commands and observations from this workspace only, using the three
staged learner-safe files and the locally created `student_work` artifacts.
Validation label: **ACTUAL LOCAL RUNS**. Shell startup repeatedly printed
unresolved numeric user/group-name warnings; those were environmental noise and
did not affect Python exit status.

## 1. Bound the inputs

I first attempted the preferred fast file listing:

```bash
pwd && rg --files -g '!student_work/**'
```

Observation: `pwd` showed the provided attempt workspace, but the command ended
with `/bin/bash: rg: command not found`. Revision: use a shallow `find` only to
identify staged filenames:

```bash
find . -maxdepth 2 -type f -print
```

It listed `.factory-workspace`, `UNIT_BRIEF.md`, `LEARNING_TASK.md`,
`SELF_CHECK.md`, and `JOB.md`. I read only the three explicitly learner-safe
packet files: `UNIT_BRIEF.md`, `LEARNING_TASK.md`, and `SELF_CHECK.md`. I did not
inspect the other two files or search outside the workspace.

## 2. Preserve unsafe-excerpt hypotheses before replacement

Four smallest-case hypotheses were written down before replacement coding:
stale mutation before rejection, conflicting-ID mutation, forged-higher-epoch
self-authorization, and exact-expiry acceptance. I rendered only the necessary
unsafe semantics in `UnsafeExcerptIncidentTests`. The actual reproduction command
and output are preserved in `INCIDENT.md`.

Observation: all four defect assertions reproduced. Revision: establish the
processing order `history/payload -> full sink fence -> transition -> history`
and use one half-open interval predicate.

## 3. First implementation compile failure

The initial implementation used frozen dataclasses, postponed annotations, and
built-in generic annotations. I checked it before writing tests:

```bash
PYTHONPATH=student_work python3 -m py_compile student_work/lease_queue.py
```

Actual failure:

```text
  File "student_work/lease_queue.py", line 7
    from __future__ import annotations
                                     ^
SyntaxError: future feature annotations is not defined
```

Hypothesis: the default interpreter was older than expected, rather than the
module containing a misspelled future feature. Diagnostic command:

```bash
python3 --version
command -v python3
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observation:

```text
Python 3.6.8
/usr/bin/python3
Python 3.11.5
```

Revision: target the command the submission actually promises—default
`python3`—instead of requiring the alternate interpreter. I replaced dataclasses
with immutable `typing.NamedTuple` values, replaced `list[...]`/`dict[...]` with
3.6-compatible typing forms, removed postponed annotations, and quoted the one
forward type reference. The repeated compile command then exited 0 with no
Python output.

Tradeoff: `NamedTuple` is less flexible than dataclasses, but exact immutable
value equality is precisely what lease and response records need.

## 4. Full deterministic suite

Command from `student_work/`:

```bash
python3 -m unittest -v test_lease_queue.py
```

Observed summary on default Python 3.6.8:

```text
Ran 17 tests in 0.004s

OK
```

The individual output reported all six `ParcelQPublicTraceTests`, all seven
`ParcelQContractTests`, and all four `UnsafeExcerptIncidentTests` as `ok`. No test
was skipped. The unsafe tests intentionally establish defect reproduction; the
safe public and contract tests establish the replacement's local assertions.

## 5. Cross-version diagnostic

I also ran the unchanged suite with the available alternate interpreter:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest -v test_lease_queue.py
```

Observed summary:

```text
Ran 17 tests in 0.002s

OK
```

This is compatibility evidence for two local interpreters, not a portability or
production claim.

## 6. Focused log inspection

I ran the exact heredoc command preserved in `INCIDENT.md` to print fence
installations and a stale delayed submission. It produced epoch-1 installation
at tick 0, epoch-2 installation at tick 3, then `FENCED` for presented old epoch
1 at tick 4. The last record showed `READY` both before and after and
`history_changed: false`.

Revision prompted by inspection: none was necessary; the fields directly
distinguished presented from installed authority. The focused trace is retained
so this conclusion can be replayed rather than trusted as prose.

## Current status and next diagnostic step

There are no known red local tests. The remaining limitations are model
boundaries, not silently resolved bugs: no real clock, concurrency, crash
recovery, disk, network, replicated coordinator, or hostile-token mechanism was
available. If this exercise were expanded, the next diagnostic step would be a
state-machine/property trace generator that enumerates short grant and delivery
sequences, followed only then by a separately authorized durable multi-process
harness. Neither was attempted, and no transfer verification was performed.
