# Validation record

Generation-time validation was performed in the allocated workspace on 2026-08-31. These observations
are evidence from this worker only; they do not replace the required independent validator. Status
remains `GENERATED` + `PARTIAL`, and `productionized` remains `false`.

## Environment

Command:

```bash
python3 --version
```

Observed: `Python 3.6.8`, exit 0. No dependency installation, network request, or upstream checkout was
attempted. The shell wrapper emitted user/group lookup warnings before some commands; those messages
were external to Sprig and did not alter command exit status.

## Executable reference validation

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -p 'test_*.py' -v
```

Observed: 24 tests ran in 0.240s, `OK`, exit 0.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -p 'test_*.py' -v
```

Observed: 34 tests ran in 0.354s, `OK`, exit 0. The reference suite includes reader boundaries,
evaluation order/scope/budgets, evaluator–VM differential cases, malformed bytecode, and CLI behavior.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -m sprig --engine vm --disassemble -e '(if false (/ 1 0) (+ 19 23))'
```

Observed exit 0 and exact Sprig output:

```text
0000 CONST 0 ; false
0001 JUMP_IF_FALSE 7
0002 LOAD /
0003 CONST 1 ; 1
0004 CONST 2 ; 0
0005 CALL 2
0006 JUMP 11
0007 LOAD +
0008 CONST 3 ; 19
0009 CONST 4 ; 23
0010 CALL 2
0011 RETURN
42
```

This smoke case also confirms the untaken division-by-zero branch was not executed.

## Expected incomplete/exercise baselines

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter python3 -m unittest public_tests.test_01_reader -v
```

Observed: 5 tests ran in 0.002s, `FAILED (errors=7)`, exit 1. Every error was an intentional milestone-1
`NotImplementedError`; the starter is not represented as a completed solution.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s debugging/step-budget -p 'test_*.py' -v
```

Observed: 1 test ran in 0.001s, `FAILED (errors=1)`, exit 1. This failure is the deliberate defect posed
by that debugging exercise; its diagnosis is confined to the exercise-local `sealed/` directory.

## Informative failed attempt retained

The first reference run used:

```bash
PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -p 'test_*.py' -v
```

Observed: 24 tests ran in 0.247s, `FAILED (failures=1)`, exit 1. `test_file_mode_reads_utf8` had written
the six literal characters `\\u2603`, which correctly produced `READ_BAD_ESCAPE` because Sprig does
not define a `\u` escape. The fixture was corrected to write the actual UTF-8 snowman character. The
final 24-test run above then passed.

## Structure, metadata, and credential-pattern check

After deleting generated `__pycache__` scratch directories, command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B sealed/validation/check_artifact.py
```

Observed exit 0:

```text
required_paths=23/23
forbidden_paths=absent (21 checked)
artifact_nodes=83 regular_files_or_directories=yes symlinks=0
manifest=exact strict_json=yes
provenance=strict_json=yes raw_sha256=1bb8ebbb6979886568adc0895e34ebe29108cf38ebfc2fee20427012e5cc75b1
credential_pattern_matches=0
```

The checker only scans the generated artifact entries, not factory control files. It rejects duplicate
JSON keys, compares `MANIFEST.yaml` to the authoritative object, verifies the immutable provenance file
bytes and snapshot identity, checks all required/forbidden paths, rejects symlinks and special files,
and searches text artifacts for common private-key, access-key, assigned-secret, and JWT patterns.

## Explicitly not performed

No randomized or coverage-guided fuzzing, benchmark, profiler run, coverage measurement, static type
analysis, transfer verification, production deployment, or independent review was performed. Those
gaps are why labels remain exactly `GENERATED` and `PARTIAL`.
