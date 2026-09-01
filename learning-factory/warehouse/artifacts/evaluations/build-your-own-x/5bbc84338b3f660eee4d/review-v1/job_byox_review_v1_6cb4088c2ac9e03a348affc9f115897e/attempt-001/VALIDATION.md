# Independent validation record

All candidate reads and executions were performed from `CANDIDATE/` unless noted. `CANDIDATE/` was not edited. Commands used bounded outer `timeout` wrappers where execution could run submitted code, and bytecode generation was disabled. The shell consistently emitted user/group lookup warnings; those warnings were external to Sprig and are omitted below.

## Toolchains

```bash
python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed: Python 3.6.8 and Python 3.11.5, both exit 0.

## Candidate suites

Exact public-suite rerun in the immutable candidate directory:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m unittest discover -s public_tests -p 'test_*.py' -v
```

Observed: exit 1; 24 tests ran, 23 passed, and `test_file_mode_reads_utf8` errored before invoking Sprig because `tempfile.mkstemp` found no usable directory among `/tmp`, `/var/tmp`, `/usr/tmp`, and the read-only candidate directory.

Rerun with temporary files directed to the writable review workspace:

```bash
timeout 30s env TMPDIR=.. PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m unittest discover -s public_tests -p 'test_*.py' -v
```

Observed on Python 3.6.8: exit 0; 24 tests ran in 0.243s, `OK`.

```bash
timeout 30s env TMPDIR=.. PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -p 'test_*.py' -v
```

Observed on Python 3.11.5: exit 0; 24 tests ran in 0.488s, `OK`.

Deeper reference suite:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m unittest discover -s sealed/reference_tests -p 'test_*.py' -v
```

Observed on Python 3.6.8: exit 0; 34 tests ran in 0.341s, `OK`.

The equivalent Python 3.11.5 command also exited 0; 34 tests ran in 0.766s, `OK`.

Documented smoke case:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m sprig --engine vm --disassemble \
  -e '(if false (/ 1 0) (+ 19 23))'
```

Observed exit 0 and exact output:

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

Intentional baselines:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  python3 -m unittest public_tests.test_01_reader -v
timeout 30s env PYTHONDONTWRITEBYTECODE=1 \
  python3 -m unittest discover -s debugging/step-budget -p 'test_*.py' -v
```

Observed: the starter command exited 1 after 5 tests with 7 intentional milestone-1 `NotImplementedError` errors. The debugging command exited 1 after its one test raised the exercise's intentional `BudgetExceeded` defect. Both match the candidate's description.

## Independent correctness probes

Data-value round trip:

```bash
timeout 10s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -c \
  'from sprig import Evaluator,default_environment,print_value,read_one; value=Evaluator().evaluate(read_one("(type nil)"),default_environment()); rendered=print_value(value); restored=read_one(rendered); print("value={0!r} rendered={1!r} restored={2!r} equal={3}".format(value,rendered,restored,value==restored)); raise SystemExit(0 if value==restored else 1)'
```

Observed exit 1:

```text
value=Symbol('nil') rendered='nil' restored=None equal=False
```

Integer grammar boundary, run with both available interpreters:

```bash
timeout 10s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -c \
  'from sprig import LanguageError,read_one; import sys; source="9"*5000
try:
 value=read_one(source); print("digits=5000 accepted={0}".format(type(value) is int)); sys.exit(0)
except LanguageError as error:
 print("digits=5000 language_error={0}".format(error.code)); sys.exit(1)'
```

Observed on Python 3.6.8 and Python 3.11.5: exit 1 and `digits=5000 language_error=READ_INTEGER`. `sys.get_int_max_str_digits()` reported 4300 on Python 3.6.8.

Large arithmetic rendering:

```bash
timeout 15s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -c \
  'import subprocess,sys; source="(* "+"9"*3000+" "+"9"*3000+")"; result=subprocess.run([sys.executable,"-m","sprig","-e",source],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10,start_new_session=True); print("returncode={0} stdout_len={1} traceback={2}".format(result.returncode,len(result.stdout),"Traceback" in result.stderr)); print(result.stderr.splitlines()[-1] if result.stderr else "stderr_empty"); raise SystemExit(1 if result.returncode != 0 or result.stderr else 0)'
```

Observed exit 1 from the probe: child return code 1, stdout length 0, `traceback=True`; stderr ended with the host `ValueError` for exceeding the 4,300-digit integer-string conversion limit.

A reviewer-authored finite matrix exercised literals, every builtin family, both branch directions and Sprig truthiness, nested calls/`do`, documented errors, and repeat disassembly. Observed: `differential_cases=55 matched_results=47 matched_errors=8 deterministic_disassembly=yes`, exit 0. A separate operand/stack/target matrix observed `malformed_vm_cases=24 all_language_errors=yes`, exit 0. These were deterministic examples, not fuzzing.

## Structure, provenance, and static inspection

```bash
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
find CANDIDATE -type l -print
find CANDIDATE -type f \( -name '*.pyc' -o -name '*.pyo' \) -print
```

Observed from the review-workspace root:

```text
1bb8ebbb6979886568adc0895e34ebe29108cf38ebfc2fee20427012e5cc75b1  CANDIDATE/PROVENANCE.json
78bd9ab86416bf7899a6dae1f7c6067e74fa18aef1362fa976a7e4c8bd203eb0  CANDIDATE/MANIFEST.yaml
```

Both `find` commands produced no paths. An independent `lstat`/strict-JSON audit counted 84 nodes including the candidate root and 64 files, with zero symlinks and zero irregular nodes. It confirmed that the manifest provenance identifier equals `PROVENANCE.json`'s snapshot identifier, found no duplicate JSON keys, and found no credential-pattern matches.

Candidate-owned checker, rerun only for claim comparison:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 python3 -B sealed/validation/check_artifact.py
```

Observed exit 0 with 23/23 required paths, 21 forbidden paths absent, 83 artifact nodes (root excluded), zero symlinks, exact manifest, strict provenance JSON, the same raw provenance hash, and zero credential-pattern matches. This script was not treated as independent proof.

Read-only syntax and prohibited-call inspection:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import pathlib; paths=sorted(pathlib.Path(".").rglob("*.py")); [compile(path.read_bytes(),str(path),"exec") for path in paths]; print("parsed_python_files={0}".format(len(paths)))'
grep -RInE '(^|[^[:alnum:]_])(eval|exec)[[:space:]]*\(|os\.(system|environ|getenv)|socket|urllib|requests' \
  starter sealed/reference
```

Observed: 37 Python files parsed, exit 0. The prohibited-call search produced no matches. AST import review found only standard-library and local modules. Static AST review found two subprocess calls, at `public_tests/test_05_cli.py:11` and `sealed/reference_tests/test_cli_reference.py:9`; neither call has `timeout` or process-group/session keywords.

A `compileall -b` attempt was inconclusive because it tried to create adjacent `.pyc` files and every immutable candidate write was denied. It changed no file. The read-only `compile(...)` pass above superseded that check.

## Limitations

- Network access and the upstream/source checkout were unavailable, so no independent similarity or upstream-license comparison was possible.
- The artifact contains recursively named `sealed` areas, but no materialized learner view or transfer receipt was provided. Actual non-disclosure is inconclusive.
- No fuzzing, benchmark, profiler, coverage, static type analysis, transfer verification, deployment, or production/security certification was performed or inferred.
- The builder's described earlier failed public run has no raw retained log in the candidate; that prose was not counted as evidence.
