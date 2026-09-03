# Independent validation record

Review date: 2026-09-02. Commands were run from `CANDIDATE/` unless noted otherwise. All mutable
temporary data was placed beside, never inside, `CANDIDATE/`, then deleted. Candidate-provided tests
and scripts are reported as corroboration, not as self-proving labels.

## Toolchain

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/unshare --version
```

Observed exit 0:

```text
Python 3.11.5
unshare from util-linux 2.32.1
```

The exact configured Python binary was the only supplied language toolchain relevant to this
Python-only pack. `/usr/bin/unshare` was additionally required for the optional Linux path. The
other configured Java, Arm, QEMU, Node, Go, NASM, GCC/binutils, Flex, Bison, and GLib roots were not
applicable and were not exercised. `rg` was unavailable, so discovery used `find`.

## Immutable inventory and provenance

An independent Python inventory accepted only regular files/directories and hashed each relative
path and content with explicit length framing. It was run before and after all checks:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c \
'import hashlib,json,pathlib,stat; root=pathlib.Path("."); entries=sorted(root.rglob("*")); files=[p for p in entries if p.is_file()]; dirs=[p for p in entries if p.is_dir()]; h=hashlib.sha256(); [(h.update(len((r:=p.relative_to(root).as_posix().encode())).to_bytes(8,"big")),h.update(r),h.update(len((d:=p.read_bytes())).to_bytes(8,"big")),h.update(d)) for p in files]; print(json.dumps({"directories":len(dirs),"files":len(files),"sha256_path_length_content_framed":h.hexdigest()},sort_keys=True))'
/usr/bin/sha256sum PROVENANCE.json
/usr/bin/sha256sum -c environment/PROVENANCE.sha256
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_pack.py
```

Observed:

```text
{"directories": 19, "files": 72, "sha256_path_length_content_framed": "f16614c71ef5400c5b289905e79bb0fcc747d9b539006307a149f22618bf804a"}
1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611  PROVENANCE.json
PROVENANCE.json: OK
OK: source pack with 72 canonical files; complete file set; forbidden paths absent; regular entries only; metadata and credential scan clean
```

The detailed initial inventory also found 19 directories, 72 files, zero symlinks, and zero special
entries. The final framed digest was identical. The candidate verifier exited 0, but it is not a
solution validator.

## Syntax and deterministic suites

Scratch used for these commands was the explicit workspace-local directory
`../.review-tmp`:

```bash
PY=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
SCRATCH="$PWD/../.review-tmp"
/usr/bin/mkdir -p "$SCRATCH"

/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$SCRATCH" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PY" -m unittest discover -s public_tests -v

/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$SCRATCH" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PY" -m unittest public_tests.checkpoints -v

/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$SCRATCH" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PY" -m unittest public_tests.checkpoints -v

/usr/bin/timeout --signal=KILL 60 /usr/bin/env TMPDIR="$SCRATCH" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PY" -m unittest discover -s sealed/reference_tests -v

/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$SCRATCH" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PY" -m unittest discover -s adversarial -v
```

Observed results:

| Check | Exit | Result |
|---|---:|---|
| Starter public discovery | 0 | 10 passed |
| Untouched-starter checkpoints | 1 | 4 ran: 1 failure, 3 `NotImplementedError` errors (documented initial red) |
| Reference checkpoints | 0 | 4 passed |
| Sealed discovery | 0 | 42 passed, exactly 2 opt-in Linux skips |
| Adversarial discovery | 0 | 4 passed |

All Python sources were independently parsed:

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 "$PY" -B -c \
'import ast,pathlib; roots=tuple(map(pathlib.Path,("starter","public_tests","environment","sealed","adversarial","debugging","review_exercises","benchmarks"))); files=sorted(p for root in roots for p in root.rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"),filename=str(p)) for p in files]; print(f"AST_OK: {len(files)} Python files")'
```

Observed exit 0: `AST_OK: 43 Python files`.

## Export and progressive-disclosure checks

```bash
DEST="$PWD/../.review-export"
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  "$PY" -B environment/export_views.py create "$DEST"
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  "$PY" -B environment/export_views.py verify "$DEST/learner" --role learner
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  "$PY" -B environment/export_views.py verify "$DEST/instructor" --role instructor
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$SCRATCH" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$DEST/learner/starter" \
  "$PY" -m unittest discover -s "$DEST/learner/public_tests" -v
```

All exited 0. Creation and verification repeatedly reported:

```json
{"files": 27, "manifest_sha256": "5188d9ae990d4a73176a5d0075713d5cbb41a95c59e0fdb7402500325b5570f2", "role": "learner"}
{"files": 72, "manifest_sha256": "da378e67aaecac51db550db98abd6a5d8180f3b5676c814e25496afe0e76ab41", "role": "instructor"}
```

An independent standard-library recomputation compared actual learner files with declared
path/size/SHA-256 tuples and directories. It observed 27 actual and 27 declared payload files,
`files_match=true`, `directories_match=true`, no symlink/special entry, and no `sealed`,
`adversarial`, `debugging`, `review_exercises`, `benchmarks`, `VALIDATION.md`,
`LICENSE_BOUNDARY.md`, or `PROVENANCE.json`. The top-level roots were exactly:

```text
AGENTS.md, CONCEPTS.md, DESIGN_QUESTIONS.md, MANIFEST.yaml, README.md,
REQUIREMENTS.md, environment, public_tests, starter
```

The exported learner public suite passed all 10 tests. Omitting answer/evaluator roots confirms the
disclosure boundary; omitting the license/provenance notice is separately recorded as a review
finding.

## Host-dependent checks

```bash
/usr/bin/timeout --signal=KILL 15 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  "$PY" -B environment/check_host.py
/usr/bin/timeout --signal=KILL 60 /usr/bin/env MINICTR_LINUX_INTEGRATION=1 \
  TMPDIR="$SCRATCH" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PY" -m unittest sealed.reference_tests.test_linux_integration -v
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$SCRATCH" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PY" -B sealed/reference_tests/readonly_preflight_probe.py
```

Observed exit 0 for all three commands:

```json
{"linux": true, "probe_exit_code": 0, "python": "3.11.5", "unshare_path": "/usr/bin/unshare", "user_namespace_probe": "AVAILABLE"}
```

The integration suite ran 2 tests and reported `OK`. The separate default-policy probe reported:

```json
{"actionable_unsupported": true, "exit_code": 69, "supported": false, "timed_out": false, "workload_started": false}
```

Thus a benign writable-rootfs launch worked and the unavailable read-only path failed closed before
workload launch. Successful read-only execution and hostile-workload isolation remain unverified.

## Independent contract probes

### Numeric conversion

The following logic was run once with `PYTHONPATH=starter` and once with
`PYTHONPATH=sealed/reference`:

```bash
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference "$PY" -B -c \
'from minictr.spec import ContainerSpec
try:
    ContainerSpec.from_mapping({"id":"probe","rootfs":"/tmp/root","command":["/bin/true"],"timeout_seconds":10**400})
    outcome="accepted"
except Exception as exc:
    outcome=type(exc).__name__
print(outcome)'
```

Both printed `OverflowError`. R1 requires `ValidationError` for configuration-boundary rejection.

### Non-finite canonical JSON

An injected fake process recorded the value passed to `communicate` for each input:

```text
input          observed wire value
NaN            NaN
Infinity       Infinity
-Infinity      -Infinity
1e1000000      Infinity
launches       4
```

The probe's assertion that no process should launch exited 1. These output tokens are not standard
JSON, so this contradicts R5's canonical-JSON boundary.

### Filesystem error normalization

```bash
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference "$PY" -B -c \
'from pathlib import Path; from minictr.paths import validate_rootfs
try:
    validate_rootfs(Path("/" + "x"*5000))
except Exception as exc:
    print(type(exc).__name__, repr(exc))'
```

Observed: `OSError OSError(36, 'File name too long')`, not `ValidationError`.

### Simultaneous lifecycle claims

An independent two-thread probe opened a separate `Registry` connection per thread, synchronized
both immediately before `claim_start`, and then reopened the database. It exited 0 and printed:

```text
[(101, 'TransitionError'), (202, 'won')] RUNNING 202
```

The winning PID is nondeterministic; exactly one winner and one transition failure are the asserted
properties.

## Benchmark-harness smoke and cleanup

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$SCRATCH" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PY" -B benchmarks/benchmark_reference.py --iterations 20
```

Observed exit 0:

```text
iterations=20
plan_total_seconds=0.008892
sqlite_lifecycle_total_seconds=0.457091
```

This only confirms harness executability. It is not controlled performance evidence and does not
support a `BENCHMARKED` label.

The exact scratch trees `../.review-export` and `../.review-tmp` were type-checked as real
directories and removed with `find <exact-path> -depth -delete`. The post-cleanup workspace retained
only its pre-existing control entries and `CANDIDATE`; the final candidate digest matched the
initial digest exactly.

## Overall limitations

- The immutable upstream baseline and network were unavailable, so the no-copy/source-license
  assertions were checked only for internal consistency.
- Candidate tests cannot prove their own labels; the independent probes above found omitted cases.
- The Linux run used only a disposable `/bin/true` fixture on one kernel/filesystem combination.
- The default read-only setup was actionable but unsupported here; successful read-only behavior is
  inconclusive.
- No fuzzing, transfer verification, hostile-workload testing, production audit, or controlled
  benchmark was performed or inferred.
