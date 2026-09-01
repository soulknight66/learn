# Independent validation record

Review date: 2026-08-31  
Workspace: the assigned review attempt  
Candidate policy: inspected read-only; no file under `CANDIDATE/` was edited

The observed shell startup also printed host account lookup warnings from
`/usr/bin/id`. Those warnings are infrastructure noise and are not candidate
diagnostics.

## Inventory and immutability

Command:

```bash
find CANDIDATE -maxdepth 5 -type f -print | sort
```

Observed: 51 regular files covering learner documents, starter code, public
tests, environment support, exercises, and sealed evaluator material.

Commands:

```bash
find CANDIDATE -type l -print
find CANDIDATE ! -type f ! -type d ! -type l -print
find CANDIDATE -type f -printf '%m %p\n' | sort
```

Observed: no symbolic links and no non-file/non-directory nodes. Ordinary files
were mode `0444`; the four executable scripts were mode `0555`. Candidate
directories were mode `2555`.

The following aggregate command was run before and after dynamic entry-point
checks:

```bash
sha256sum $(find CANDIDATE -type f -print | sort) | sha256sum
```

Observed both times:

```text
9e8f6fb5452f8907fbc7999b9b2e79d943873ee7a7c144f900b161f4f9d8a1a8  -
```

This is a review-local aggregate over sorted path arguments, not a submitted
artifact claim or a standard release-tree format.

## Toolchain discovery

Commands:

```bash
command -v fpc
command -v ppcx64
command -v make
python3 --version
```

Observed:

```text
fpc: exit 1, no stdout
ppcx64: exit 1, no stdout
/usr/bin/make
Python 3.6.8
```

A bounded search of common `/usr`/`/usr/local` locations and `/arm/tools` to
depth six also found no `fpc` or `ppcx64`. No Pascal lint/compiler, container
runtime, or alternate Pascal translator was found. Native validation was
therefore unavailable.

## Syntax and metadata checks

Command:

```bash
bash -n CANDIDATE/environment/check.sh
```

Observed: exit 0, no output.

Command (source parsing only; bytecode caches disabled):

```bash
python3 -B -c "import ast, pathlib; paths=['CANDIDATE/public_tests/run_tests.py','CANDIDATE/sealed/reference_tests/run_reference_tests.py','CANDIDATE/sealed/benchmarks/benchmark_driver.py']; [ast.parse(pathlib.Path(p).read_text(), filename=p) for p in paths]; print('AST parse PASS:', len(paths), 'Python files')"
```

Observed:

```text
AST parse PASS: 3 Python files
```

Command (strict JSON parsing):

```bash
python3 -B -c "import json, pathlib; paths=['CANDIDATE/MANIFEST.yaml','CANDIDATE/PROVENANCE.json','CANDIDATE/sealed/adversarial/cases.json']; objs=[json.loads(pathlib.Path(p).read_text()) for p in paths]; print('strict JSON PASS:', len(objs), 'files')"
```

Observed:

```text
strict JSON PASS: 3 files
```

Independent Python assertions also established:

- manifest/provenance schema versions are 1;
- project ID, source ID, and source commit agree across their repeated fields;
- `MANIFEST.yaml.provenance_sha256` equals
  `PROVENANCE.json.snapshot_sha256`;
- labels are exactly `GENERATED`, `PARTIAL`;
- independent validation is `REQUIRED` and productionized is false;
- adversarial case IDs are unique; and
- the strict base64 seed `cHJpbnQgMTsA` decodes to `print 1;` followed by NUL.

Observed metadata byte hashes match the submitted validation record:

```text
ae785b7b18135dfce203f576beb7db5c012920046b52d851b33fa8a5b50932cc  CANDIDATE/MANIFEST.yaml
8dec1885294f3e1e88f20ce3eaaec0d6c3cf80e4831e5cb702b07bba4db4a7e4  CANDIDATE/PROVENANCE.json
```

## Build recipe resolution

Commands:

```bash
make -n -C CANDIDATE/starter
make -n -C CANDIDATE/sealed/reference
```

Observed: both exited 0 and printed `mkdir -p bin units` followed by the expected
`fpc -Mobjfpc -Sh ...` invocation. These were GNU Make dry runs. No compiler was
started, no directory was created, and this is not `BUILDS` evidence.

An actual Make invocation was not performed: Free Pascal was already confirmed
absent, and its declared output directories are inside the immutable candidate.

## Published entry points

Command:

```bash
timeout 10s bash CANDIDATE/environment/check.sh
```

Observed: exit 2.

```text
PARTIAL: Pascal compiler 'fpc' is unavailable and MICA_BIN is not executable
```

Command:

```bash
timeout 10s env PYTHONDONTWRITEBYTECODE=1 python3 -B CANDIDATE/public_tests/run_tests.py
```

Observed: exit 1. `setUpClass` reported that
`CANDIDATE/starter/bin/mica` was not a regular file; unittest reported:

```text
Ran 0 tests in 0.001s
FAILED (errors=1)
```

Command:

```bash
timeout 10s env PYTHONDONTWRITEBYTECODE=1 python3 -B CANDIDATE/sealed/reference_tests/run_reference_tests.py
```

Observed: exit 1. `setUpClass` reported that
`CANDIDATE/sealed/reference/bin/mica` was not an executable regular file;
unittest reported:

```text
Ran 0 tests in 0.001s
FAILED (errors=1)
```

These are setup failures caused by the unavailable executable. They neither pass
nor fail Mica behavior.

## Static correctness and harness review

All Pascal and Python source plus the normative requirements were read. Static
inspection found the reference design consistent in the following areas:

- ASCII token boundaries, comments, CR/LF location updates, keyword matching,
  and checked decimal accumulation;
- recursive-descent precedence and associativity;
- declaration-before-visibility behavior, global slot allocation, and compile
  errors for unresolved names/redeclarations;
- if/else and while jump patching;
- VM operand order, comparison normalization, division/remainder zero checks,
  the narrow arithmetic domain, condition popping, and instruction 100001
  rejection; and
- CLI mode separation, diagnostic shape, and documented exit-code mapping.

This is static review evidence only. Pascal syntax, compiler warnings, exception
behavior, exact `Format` behavior, native integer semantics, and end-to-end output
remain inconclusive without compilation.

AST inspection counted 12 public and 17 sealed test methods. Across the three
Python programs it found five `subprocess.run` call sites. Every call has a
timeout and captured stdout/stderr, but none has a process-group/session keyword;
the programs contain no `os.chmod` call. Manual inspection additionally found an
unbounded `make` call in `environment/check.sh`. The public addition-overflow test
at lines 96-99 does not assert return status or stdout.

## Content and boundary checks

A read-only Python scan of all 51 files observed:

```text
credential-pattern hits: 0
UTF-8 decode failures: 0
files containing literal NUL: 0
symlinks: 0
```

The credential patterns covered common private-key headers, AWS access-key
shapes, GitHub/OpenAI token shapes, and quoted secret/password/API-key
assignments. This limited pattern scan is not a general secret-proof claim.

Manual disclosure inspection found solution-bearing materials under root
`CANDIDATE/sealed/` and no obvious solution copy outside that subtree. Because
the review workspace exposes the complete bundle, it cannot prove what a learner
view contains.

`LICENSE_BOUNDARY.md` clearly distinguishes CC0 catalog metadata from the linked
resource with `NOASSERTION`. No standalone license grant for the independently
generated code/tests/prose was found. Upstream comparison was unavailable, so
the submitted no-copy assertion was not independently verified.

## Limitations and labels

- `BUILDS`: not established.
- `TESTED`: not established; both suites ran zero behavioral tests.
- `FUZZED`: not performed.
- `BENCHMARKED`: not performed.
- `REVIEWED`: this independent report records a review, but does not mutate or
  promote the candidate manifest.
- `TRANSFER_VERIFIED`: not performed; no learner-view artifact was supplied.
- `PRODUCTIONIZED`: not established and explicitly false.

The evidence supports retaining `GENERATED + PARTIAL` and returning the artifact
for revision/independent native validation.
