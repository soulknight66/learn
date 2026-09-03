# Independent validation record

Date: 2026-09-02. Candidate files were treated as immutable. Commands ran with working directory
`CANDIDATE/` unless stated otherwise. Temporary files used the workspace-local `.review-tmp/`, which
was empty and removed after testing.

From the workspace root, scratch setup exited 0 with no output:

```bash
mkdir -p .review-tmp
```

## Toolchain

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
/usr/bin/unshare --version
```

Observed: all exited 0; output was `Python 3.11.5`, `3.11.5`, and
`unshare from util-linux 2.32.1`, respectively. Python was invoked from the configured read-only
toolchain by its exact absolute path. No other configured language toolchain was needed for this
Python-only artifact.

## Replay of submitted evidence

This is the command recorded at `CANDIDATE/VALIDATION.md:52`, replayed literally:

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp" + PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter + /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 + -m unittest discover -s public_tests -v
```

Observed exit 127:

```text
/usr/bin/env: ‘+’: No such file or directory
```

The same literal separator defect occurs on validation lines 61, 72, 78, 86, 97, 168, 178, 186,
and 196. The following independent commands remove only those invalid separators.

## Deterministic suites

The absolute `TMPDIR` used below was
`/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp`.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.checkpoints -v
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.checkpoints -v
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s adversarial -v
```

Observed, in order:

- Exit 0: 10 tests, `OK`.
- Exit 1: 4 tests, `FAILED (failures=1, errors=3)` at the documented untouched-starter boundaries.
- Exit 0: 4 tests, `OK`.
- Exit 0: 29 tests, `OK (skipped=1)`; only the explicit integration test was skipped.
- Exit 0: 4 tests, `OK`.

## Packaging, syntax, and provenance

```bash
/usr/bin/timeout --signal=KILL 30 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_pack.py
/usr/bin/timeout --signal=KILL 30 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import ast,pathlib; files=sorted(pathlib.Path(".").rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in files]; print(f"AST_OK: {len(files)} Python files")'
/usr/bin/sha256sum PROVENANCE.json
/usr/bin/sha256sum -c environment/PROVENANCE.sha256
```

Observed: all exited 0. The verifier reported 24 required files and clean metadata/credential scans;
the syntax check reported `AST_OK: 37 Python files`; both digest commands reported
`1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611` and the sidecar reported
`PROVENANCE.json: OK`.

The verifier's `REQUIRED` list was also inspected. It names documentation and metadata but no Python
implementation or test file, so this successful check is packaging hygiene evidence, not a complete
artifact-integrity proof.

## Host and kernel checks

```bash
/usr/bin/timeout --signal=KILL 15 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_host.py
/usr/bin/timeout --signal=KILL 30 /usr/bin/env MINICTR_LINUX_INTEGRATION=1 TMPDIR="/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest sealed.reference_tests.test_linux_integration -v
```

Observed: both exited 0. The probe returned
`{"linux": true, "probe_exit_code": 0, "python": "3.11.5", "unshare_path": "/usr/bin/unshare", "user_namespace_probe": "AVAILABLE"}`.
The writable-root `/bin/true` integration ran one test and passed.

The independent read-only check ran from the workspace root with
`PYTHONPATH=CANDIDATE/sealed/reference`. It duplicated the supplied disposable `/bin/true` fixture
but set `readonly_root` to true, then executed `build_launch_plan` and `Runner.run` under the same
30-second outer timeout:

An initial attempt from the immutable `CANDIDATE/` working directory failed before Python ran because
bash could not create its here-document temporary file there. Rerunning the same probe from the
writable workspace root produced the material result below.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_1a8ceb4bc1f1615b11e7acbae6748cdb/attempt-001/.review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=CANDIDATE/sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import json
from pathlib import Path
import shutil
import tempfile
from minictr.planner import build_launch_plan
from minictr.runner import Runner
from minictr.spec import ContainerSpec

deps = (Path("/bin/true"), Path("/lib64/libc.so.6"), Path("/lib64/ld-linux-x86-64.so.2"))
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary) / "root"
    (root / "bin").mkdir(parents=True)
    (root / "lib64").mkdir()
    (root / "proc").mkdir()
    shutil.copy2(deps[0], root / "bin/true")
    shutil.copy2(deps[1], root / "lib64/libc.so.6")
    shutil.copy2(deps[2], root / "lib64/ld-linux-x86-64.so.2")
    spec = ContainerSpec.from_mapping({
        "id": "readonly", "rootfs": str(root), "command": ["/bin/true"],
        "timeout_seconds": 10, "readonly_root": True, "network": False,
    })
    plan = build_launch_plan(spec, "/usr/bin/unshare")
    payload = json.dumps(spec.to_mapping(), sort_keys=True, separators=(",", ":")).encode()
    result = Runner().run(plan, payload)
    print(json.dumps({"exit_code": result.exit_code, "stderr": result.stderr.decode(errors="replace"), "timed_out": result.timed_out}, sort_keys=True))
    raise SystemExit(0 if result.exit_code == 0 and not result.timed_out else 1)
PY
```

Observed exit 1 from the probe because the supervised child returned 126, did not time out, and
reported `PermissionError: [Errno 1] Operation not permitted` for the temporary root path. The
writable-mode pass and target path localize the host-specific failure to the read-only remount path.

## Disclosure and inventory

```bash
find . -type f | wc -l
find . -type l | wc -l
find . -type f -name '*.py' | wc -l
find sealed adversarial debugging review_exercises -type f | wc -l
```

Observed: 65 files, 0 symbolic links, 37 Python files, and 35 files in the named evaluator/sealed
trees. Direct reads confirmed that the full reference, evaluator tests, and answer files are present
in this same artifact despite their learner-invisible descriptions.

## Limitations

- `rg` and `git` were unavailable; `find` and direct reads were used instead.
- Network and the immutable upstream snapshot were unavailable, so external provenance and license
  assertions were not independently compared with source material.
- No fuzzing, controlled benchmark, transfer verification, hostile-workload containment, output
  stress, crash recovery, or cross-kernel/filesystem matrix was run.
- The read-only remount result applies to this supplied NFS-backed environment.
- This independent review does not publish a `REVIEWED` validation label.

Finally, from the workspace root, the first command exited 0 with no output, proving scratch was
empty; the second exited 0 and removed it:

```bash
find .review-tmp -mindepth 1 -maxdepth 4 -print
rmdir .review-tmp
```
