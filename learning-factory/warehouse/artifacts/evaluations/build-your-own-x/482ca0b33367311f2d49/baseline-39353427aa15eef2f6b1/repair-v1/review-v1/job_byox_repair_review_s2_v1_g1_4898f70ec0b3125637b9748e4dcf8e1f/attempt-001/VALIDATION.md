# Independent validation evidence

Review date: 2026-09-02 (America/Chicago). Commands ran from the attempt workspace unless a command
explicitly changes to `CANDIDATE`. The candidate was read-only (`CANDIDATE` mode `2555`); all scratch
was placed under the sibling `.review-tmp/` and removed after use.

The command wrapper prefixed most output with unrelated identity lookup warnings:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

They did not replace the captured child exit status.

For compactness, the following exact paths are denoted below:

```bash
REVIEW_ROOT=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_4898f70ec0b3125637b9748e4dcf8e1f/attempt-001
PY=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
JAVA=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java
```

## Toolchains

Commands:

```bash
/usr/bin/timeout 10s "$PY" --version
/usr/bin/timeout 10s "$JAVA" -version
```

Both exited `0`:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java is configured but is not useful to this Python-only pack. `rg` and `git` were not available;
bounded `find`, `grep`, and Python hashing were used instead.

## Inventory and immutable records

The inventory digest hashes each sorted relative path plus NUL plus that file's SHA-256 digest:

```bash
env PYTHONDONTWRITEBYTECODE=1 "$PY" -c '
import hashlib, pathlib
root = pathlib.Path("CANDIDATE")
files = sorted(path for path in root.rglob("*") if path.is_file())
digest = hashlib.sha256()
for path in files:
    digest.update(path.relative_to(root).as_posix().encode() + b"\0")
    digest.update(hashlib.sha256(path.read_bytes()).digest())
print(f"candidate_files={len(files)} inventory_sha256={digest.hexdigest()}")
'
```

Observed before review and again after all candidate checks, exit `0`:

```text
candidate_files=59 inventory_sha256=5baec46c6f5662b5e0808f8552de00759cbc69c01da0667de2a56fbace3ec0a0
```

The manifest/provenance parsing audit observed a sorted unique 27-path allowlist, matching project and
snapshot identifiers, and these byte hashes:

```text
4eb8b23f9c116db38a01876763e2e4f97e22c4219c9446bf949bb7e374c43123  CANDIDATE/MANIFEST.yaml
266aadf01d684512a09ebed6ddd12fdbb424c6b2c27bb676147ce4df18d37705  CANDIDATE/PROVENANCE.json
```

The manifest values remained `validation_labels=["GENERATED","PARTIAL"]`,
`productionized=false`, and `independent_validation="REQUIRED"`.

One initial inventory one-liner exited nonzero with an f-string quoting `SyntaxError`; it read no less
data and changed no file. The corrected command above produced the recorded result.

## Syntax and supplied suites

Scratch directories were created outside `CANDIDATE`. Commands used the configured interpreter and
were bounded by `/usr/bin/timeout`:

```bash
mkdir -p "$REVIEW_ROOT/.review-tmp/compile" \
  "$REVIEW_ROOT/.review-tmp/public" \
  "$REVIEW_ROOT/.review-tmp/sealed" \
  "$REVIEW_ROOT/.review-tmp/starter"

(cd CANDIDATE && /usr/bin/timeout 30s env \
  PYTHONPYCACHEPREFIX="$REVIEW_ROOT/.review-tmp/compile" \
  "$PY" -m compileall -q -f starter public_tests sealed/reference sealed/reference_tests \
  environment/export_student_view.py)

(cd CANDIDATE && /usr/bin/timeout 30s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp/public" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference "$PY" -m unittest discover -s public_tests -v)

(cd CANDIDATE && /usr/bin/timeout 45s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp/sealed" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference "$PY" -m unittest discover -s sealed/reference_tests -v)

(cd CANDIDATE && /usr/bin/timeout 30s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp/starter" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=starter "$PY" -m unittest discover -s public_tests -v)
```

Observed results:

```text
compileall: exit 0, no diagnostics
reference public suite: exit 0, Ran 11 tests in 0.958s, OK
reference sealed suite: exit 0, Ran 34 tests in 6.169s, OK
starter public suite: exit 1, Ran 11 tests in 0.121s, FAILED (errors=17)
```

The starter errors were the expected numbered `NotImplementedError` sites; they are evidence of an
unimplemented learner baseline, not a passing implementation.

## Student-view boundary and license audit

Commands:

```bash
(cd CANDIDATE && /usr/bin/timeout 10s env PYTHONDONTWRITEBYTECODE=1 \
  "$PY" environment/export_student_view.py --source . --check)

(cd CANDIDATE && /usr/bin/timeout 15s env PYTHONDONTWRITEBYTECODE=1 \
  "$PY" environment/export_student_view.py --source . \
  --destination "$REVIEW_ROOT/.review-tmp/student-view")

(cd "$REVIEW_ROOT/.review-tmp/student-view" && /usr/bin/timeout 10s \
  env PYTHONDONTWRITEBYTECODE=1 "$PY" environment/export_student_view.py --source . --check)
```

Each exited `0` and each exporter/check invocation emitted:

```json
{"files":27,"status":"ok"}
```

A Python audit compared the actual exported regular-file path set with the JSON allowlist and SHA-256
compared every exported file with its source. Observed exit `0`:

```text
actual_files=27 exact_path_set=True byte_mismatches=0 nonregular=0 forbidden_roots=[]
```

A separate content/path audit looked for names containing `license`, `copying`, `notice`, or
`provenance`, and for the explicit phrases `permission is granted`, `CC0-1.0`, or
`no permission is asserted`. It exited `0` and observed:

```text
named_license_or_provenance_files=[]
explicit_license_term_files=[]
```

Thus the technical sealed-material boundary works for this snapshot, but the exported copy omits the
notice and provenance that `CANDIDATE/LICENSE_BOUNDARY.md:10-16` directs copies to preserve.

## Independent contract regressions

Both checks used the sealed reference and scratch outside `CANDIDATE`.

### Derived whiteout target must fail before mutation

Command body:

```python
import tempfile
from pathlib import Path
from pydocklet import LayerApplier
from sealed.reference_tests.helpers import write_regular_layer

with tempfile.TemporaryDirectory() as temporary:
    work = Path(temporary)
    rootfs = work / "rootfs"
    rootfs.mkdir()
    victim = rootfs / "victim"
    victim.write_bytes(b"preserve")
    layer = write_regular_layer(
        work / "case.tar",
        [(".wh.victim", b"", 0o644), (".wh...", b"", 0o644)],
    )
    observed = None
    try:
        LayerApplier().apply(layer, rootfs)
    except Exception as exc:
        observed = type(exc).__name__
    print(f"exception={observed} victim_exists={victim.exists()}")
    assert observed == "PathEscape" and victim.exists()
```

It was supplied to this bounded command:

```bash
(cd CANDIDATE && /usr/bin/timeout 20s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp/custom" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference "$PY" -c '<command body above>')
```

Observed exit `1`:

```text
exception=PathEscape victim_exists=False
AssertionError
```

The unsafe target did not escape, but rejection occurred after the preceding whiteout deleted the
victim, violating the preflight/no-mutation contract.

### Directory normalization must not depend on umask

Command body:

```python
import os
import tempfile
from pathlib import Path
from pydocklet import LayerApplier
from sealed.reference_tests.helpers import write_regular_layer

with tempfile.TemporaryDirectory() as temporary:
    work = Path(temporary)
    layer = write_regular_layer(work / "case.tar", [("implicit/file", b"x", 0o644)])
    rootfs = work / "rootfs"
    previous = os.umask(0o077)
    try:
        LayerApplier().apply(layer, rootfs)
    finally:
        os.umask(previous)
    root_mode = rootfs.stat().st_mode & 0o777
    implicit_mode = (rootfs / "implicit").stat().st_mode & 0o777
    print(f"root_mode={root_mode:#05o} implicit_mode={implicit_mode:#05o}")
    assert root_mode == implicit_mode == 0o755
```

It was run with the same bounded environment as the preceding command. Observed exit `1`:

```text
root_mode=0o700 implicit_mode=0o700
AssertionError
```

## Candidate validation-recipe reproducibility

The candidate's validation document deletes `environment/.validation-tmp` and later names that absent
path as `TMPDIR`. This diagnostic used the same setting after confirming the path was absent:

```bash
(cd CANDIDATE && test ! -e environment/.validation-tmp && /usr/bin/timeout 10s \
  env TMPDIR=environment/.validation-tmp PYTHONDONTWRITEBYTECODE=1 \
  "$PY" -c 'import os,tempfile; print("configured_TMPDIR=" + os.environ["TMPDIR"]); \
print("effective_tempdir=" + tempfile.gettempdir())')
```

Observed exit `1`:

```text
configured_TMPDIR=environment/.validation-tmp
FileNotFoundError: [Errno 2] No usable temporary directory found in
['environment/.validation-tmp', '/tmp', '/var/tmp', '/usr/tmp', '.../CANDIDATE']
```

The passing suite observations were independently reproduced only after this review explicitly made
scratch outside the immutable candidate. The recorded recipe therefore lacks a necessary precondition
or deletes it too early.

## Static audits and cleanup

Bounded recursive scans found no Python call matching `.extract(`, `.extractall(`, or `shell=True`, no
common AWS/private-key/password/token signature, no nonregular candidate entry, and no `__pycache__`,
`.pyc`, or `.validation-tmp` residue under `CANDIDATE`. Starter/public code contained no import of the
sealed implementation. These scans are pattern checks, not proof against obfuscation or dynamic calls.

The actual export and all review scratch were deleted after inspection. The final candidate inventory
remained 59 files with the same digest
`5baec46c6f5662b5e0808f8552de00759cbc69c01da0667de2a56fbace3ec0a0`.

## Limitations

- Network access and upstream content were unavailable; no-copy and upstream-license assertions were
  not independently source-compared.
- The external factory inventory was unavailable, so baseline and remediation identifiers were not
  independently recomputed.
- No fuzzing, benchmark, profiling, hostile execution, privileged isolation, cross-host transfer,
  deployment, or production security assessment was performed.
- Java was available but irrelevant. `git` and `rg` were unavailable.
- A PASS verdict from this review would be advisory only; this review assigns no validation label.
