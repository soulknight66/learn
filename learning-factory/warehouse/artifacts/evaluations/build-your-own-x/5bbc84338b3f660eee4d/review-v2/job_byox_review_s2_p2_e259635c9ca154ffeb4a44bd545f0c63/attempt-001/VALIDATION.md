# Independent validation evidence

Review date: 2026-09-02  
Candidate: immutable `CANDIDATE/`  
Verdict supported by these observations: `REVISE`

Commands were run from `CANDIDATE/` unless a command explicitly says it ran from the writable attempt root. `PYTHONDONTWRITEBYTECODE=1` was used for executable checks. No candidate file was edited.

## Toolchains

Exact command:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed stdout, exit 0:

```text
Python 3.11.5
```

Exact command:

```bash
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Observed stderr, exit 0:

```text
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java is available but not useful to this Python pack.

## Syntax and supplied suites

Exact syntax command:

```bash
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'from pathlib import Path; paths=sorted(Path(".").rglob("*.py")); [compile(p.read_text(encoding="utf-8"), str(p), "exec") for p in paths]; print(f"syntax_ok files={len(paths)}")'
```

Observed stdout, exit 0:

```text
syntax_ok files=29
```

This uses host `compile` only as an artifact syntax check; the reference contains no call to it for Pebble source.

Exact sealed-suite command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```

Observed summary, exit 0:

```text
Ran 49 tests in 0.669s

OK
```

Exact public-suite command corresponding to the builder evidence:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed summary, exit 1:

```text
Ran 19 tests in 0.334s

FAILED (errors=1)
```

The sole error came from `tempfile.TemporaryDirectory` before Pebble ran: this sandbox had no usable default temp directory among `/tmp`, `/var/tmp`, `/usr/tmp`, or the read-only candidate root. The same suite was rerun with an explicit writable temp location:

```bash
TMPDIR=.. PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed summary, exit 0:

```text
Ran 19 tests in 0.402s

OK
```

The intentionally incomplete starter was checked compactly with the pinned runtime:

```bash
TMPDIR=.. PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import io, unittest; suite=unittest.defaultTestLoader.discover("public_tests"); result=unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite); print(f"tests_run={result.testsRun} failures={len(result.failures)} errors={len(result.errors)} successful={result.wasSuccessful()}")'
```

Observed stdout, command exit 0:

```text
tests_run=19 failures=3 errors=21 successful=False
```

The runner command itself exits 0 because it reports the result rather than forwarding it. The failures are the expected `NotImplementedError`/CLI consequences and confirm the candidate did not disguise the starter as complete.

Exact CLI smoke command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m pebble.cli -e '(let ((x 6) (y 7)) (* x y))'
```

Observed stdout, exit 0:

```text
42
```

## Learner-command reproducibility

The primary learner documents use generic `python3`. Exact observation:

```bash
python3 --version
```

```text
Python 3.6.8
```

With `TMPDIR` supplied only to remove the unrelated tempfile constraint, the documented command shape still fails:

```bash
TMPDIR=.. PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter python3 -m unittest discover -s public_tests
```

Observed summary, exit 1:

```text
Ran 5 tests in 0.010s

FAILED (errors=5)
```

The observed causes included `TypeError: unsupported operand type(s) for |` while importing the Python-3.11 scaffold and Python 3.6 rejecting `subprocess.run(..., text=True)`.

## Independent semantic and VM probes

This command ran from the writable attempt root because the shell could not materialize a here-document while its working directory was immutable:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=CANDIDATE/sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pebble import Interpreter, read_one
from pebble.compiler import Instruction, Program
from pebble.vm import VirtualMachine

def observe(name, operation):
    try:
        value = operation()
    except BaseException as error:
        print(f"{name}: raised={type(error).__name__} message={error}")
    else:
        print(f"{name}: returned={value!r}")

observe("integer_5000_digits", lambda: read_one("9" * 5000))
observe("valid_nesting_1100", lambda: read_one("(" * 1100 + "0" + ")" * 1100))
interpreter = Interpreter(output=lambda _text: None)
observe("empty_predicate_integer", lambda: interpreter.eval_source("(empty? 1)"))
program = Program(
    (
        Instruction("CONST", 0),
        Instruction("JUMP_IF_FALSE", 99),
        Instruction("CONST", 1),
        Instruction("RETURN"),
    ),
    (True, 42),
)
observe("untaken_invalid_conditional_jump", lambda: VirtualMachine(interpreter).run(program))
PY
```

Observed stdout, exit 0:

```text
integer_5000_digits: raised=ValueError message=Exceeds the limit (4300 digits) for integer string conversion: value has 5000 digits; use sys.set_int_max_str_digits() to increase the limit
valid_nesting_1100: raised=RecursionError message=maximum recursion depth exceeded in comparison
empty_predicate_integer: returned=False
untaken_invalid_conditional_jump: returned=42
```

`empty?` is recorded without treating it as a failure because “true only for an empty list or nil” can reasonably define a total predicate. The invalid integer/nesting host exceptions and accepted malformed jump are findings.

The 5,000-digit case was also exercised through the CLI using the configured binary in a bounded subprocess. Observed:

```text
returncode=1
stdout_empty=True
stderr_has_error_prefix=False
stderr_has_traceback=True
stderr_last_line=ValueError: Exceeds the limit (4300 digits) for integer string conversion: value has 5000 digits; use sys.set_int_max_str_digits() to increase the limit
```

This contradicts the required controlled `error: <message>`/status-2 CLI boundary for language failures.

## Provenance, structure, and implementation audit

Independent canonical JSON hashing and identifier comparisons observed:

```text
manifest_canonical_sha256=0a134783939d3d2bd9fc51f0ab33ef43cb40e4c86dc52feceb41248b0886b18e
provenance_canonical_sha256=17238e9005ea6ad305702b2fd5f18b9693608e3ccf4bf89881f929bb46002422
manifest_provenance_matches_canonical=False
manifest_provenance_matches_snapshot_field=True
project_ids_match=True
source_ids_match=True
source_commits_match=True
```

Raw file hashing additionally observed:

```bash
/usr/bin/sha256sum PROVENANCE.json MANIFEST.yaml
```

```text
29e34b3cd43a74f15a4aa03e3876f84aa472e9be55232b4140526e21b6233f92  PROVENANCE.json
4bbb4ef15941e6f35aa8afa94088a6910c3cabe9ed6294a373bfcf4c3a9438d5  MANIFEST.yaml
```

Thus the manifest's `provenance_sha256` is an internally linked source-snapshot value, not a checksum of the submitted provenance document. The unavailable source snapshot prevents independent recomputation of that value.

An AST walk over every submitted Python file observed:

```text
non_stdlib_import_roots=[]
builtin_eval_exec_compile_calls=[]
shell_true_calls=[]
```

The independently executed structure suite also found all required paths, no forbidden top-level paths, no unusual filesystem objects, and no credential-shaped content. Direct access inspection observed:

```text
path_access starter/pebble/interpreter.py: mode=-r--r----- readable=True
path_access sealed/reference/pebble/interpreter.py: mode=-r--r----- readable=True
path_access debugging/closure_parent/sealed/ANSWER.md: mode=-r--r----- readable=True
```

The combined artifact therefore does not itself enforce a learner/sealed boundary.

## Limitations

- No network or upstream source was accessed. The source/catalog snapshot, linked resource, and canonical snapshot-hash procedure were unavailable, so origin and license assertions were checked only for internal consistency and honest scoping.
- The exact public-suite command could not complete one tempfile-dependent case under this review sandbox's permissions; the explicit `TMPDIR=..` rerun isolates and resolves that environment constraint.
- A separate orchestrator may build a learner-only view, but no such view, filter rule, or captured audit is present in the candidate.
- No fuzzing, benchmarking, transfer, security, production, or compatibility-matrix validation was run. No corresponding label is claimed.
- A passing reviewer verdict would still be advisory. Only orchestrator-captured acceptance may publish `REVIEWED`.
