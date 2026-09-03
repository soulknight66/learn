# Validation record — repair generation 1

Observed on 2026-09-02 in the allocated repair workspace. These are builder-side observations, not
independent validation. The immutable manifest remains `GENERATED` + `PARTIAL`, requires independent
validation, and keeps `productionized: false`.

## Toolchain and interpreter preflight

The configured read-only Python toolchain was invoked by its exact absolute path:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/python3 --version
```

Observed exit 0 for both commands:

```text
Python 3.11.5
Python 3.6.8
```

All Python checks below therefore use
`/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`. Learner quick starts now set a
configurable `PYTHON311` to that supplied path and perform a 3.11-or-newer preflight before tests;
they no longer invoke the incompatible bare `python3`.

The exact documented preflight was exercised with both interpreters:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
/usr/bin/python3 -c \
  'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
```

The configured interpreter exited 0 and printed `3.11.5`. The system interpreter exited 1 and
printed `3.6.8` followed by `Python 3.11+ required`.

A workspace-local temporary root was created for `tempfile` because system temporary directories
are not assumed writable:

```bash
mkdir -p .validation-tmp
```

Observed exit 0 with no output.

## Deterministic suites and stage checkpoints

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" +  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 +  -m unittest discover -s public_tests -v
```

Observed exit 0: `Ran 10 tests in 0.136s`, `OK`. Discovery intentionally covers the supplied
warm-up and ignores `public_tests/checkpoints.py`, whose name is outside the `test*.py` pattern.

The new learner-owned checkpoints were deliberately run against the untouched starter:

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" +  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 +  -m unittest public_tests.checkpoints -v
```

Observed exit 1: `Ran 4 tests in 0.038s`, `FAILED (failures=1, errors=3)`. The failures were the
documented stage-3 child bound assertion and the stage-3 planner, stage-4 registry, and stage-5
runner `NotImplementedError` boundaries. This is an intentional initial-red progress signal, not a
passing validation claim.

The same public checkpoints were then run against the sealed reference:

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" +  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 +  -m unittest public_tests.checkpoints -v
```

Observed exit 0: `Ran 4 tests in 0.086s`, `OK`.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" +  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 +  -m unittest discover -s sealed/reference_tests -v
```

Observed final code run exit 0: `Ran 29 tests in 0.536s`, `OK (skipped=1)`. The skip is the
explicitly opt-in Linux integration case. The 29 tests include RFC-3339 rejection at all three
registry entry points and an isolated provenance-verifier mutation regression.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" +  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 +  -m unittest discover -s adversarial -v
```

Observed exit 0: `Ran 4 tests in 0.131s`, `OK`.

## RFC 3339 remediation probe

The three forms accepted by the prior implementation were exercised through `create`,
`claim_start`, and `finish`:

```bash
/usr/bin/timeout --signal=KILL 20 /usr/bin/env TMPDIR="$PWD/.validation-tmp" +  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import json
from pathlib import Path
import tempfile
from minictr.errors import ValidationError
from minictr.registry import Registry
from minictr.spec import ContainerSpec

candidates = (
    "2026-W01-1T03:04:05+00:00",
    "20260102T030405+00:00",
    "2026-01-02Q03:04:05+00:00",
)
rejected = {"claim_start": 0, "create": 0, "finish": 0}
with tempfile.TemporaryDirectory() as temporary:
    registry = Registry(Path(temporary) / "state.sqlite3")
    for index, timestamp in enumerate(candidates):
        spec = ContainerSpec.from_mapping({
            "id": f"bad{index}", "rootfs": "/tmp/root", "command": ["/bin/true"]
        })
        try:
            registry.create(spec, timestamp)
        except ValidationError:
            rejected["create"] += 1
    lifecycle = ContainerSpec.from_mapping({
        "id": "lifecycle", "rootfs": "/tmp/root", "command": ["/bin/true"]
    })
    registry.create(lifecycle, "2026-01-02T03:04:05Z")
    for timestamp in candidates:
        try:
            registry.claim_start("lifecycle", 123, timestamp)
        except ValidationError:
            rejected["claim_start"] += 1
    registry.claim_start("lifecycle", 123, "2026-01-02T03:04:06Z")
    for timestamp in candidates:
        try:
            registry.finish("lifecycle", 0, "/tmp/lifecycle.log", timestamp)
        except ValidationError:
            rejected["finish"] += 1
    registry.close()
print(json.dumps(rejected, sort_keys=True))
PY
```

Observed exit 0 and exactly:

```json
{"claim_start": 3, "create": 3, "finish": 3}
```

## Provenance binding, syntax, and packaging

```bash
sha256sum PROVENANCE.json
sha256sum -c environment/PROVENANCE.sha256
```

Observed exit 0 and:

```text
1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611  PROVENANCE.json
PROVENANCE.json: OK
```

The manifest's immutable `provenance_sha256` continues to identify the source snapshot. The exact
provenance-document SHA-256 above is separately declared and hard-coded in the verifier. The
reference regression test copied the provenance document to an isolated temporary root, changed a
semantic field while retaining the snapshot ID, recomputed the sidecar, and observed both the
canonical-document and canonical-declaration checks reject it.

```bash
/usr/bin/timeout --signal=KILL 30 +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 +  environment/verify_pack.py
```

Observed exit 0:

```text
OK: 24 required files; forbidden paths absent; regular entries only; metadata and credential scan clean
```

```bash
/usr/bin/timeout --signal=KILL 30 +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c +  'import ast,pathlib; files=sorted(p for p in pathlib.Path(".").rglob("*.py") if not any(part in {"PRIOR_BUILD", "PRIOR_REVIEW"} for part in p.parts)); [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in files]; print(f"AST_OK: {len(files)} Python files")'
```

Observed exit 0: `AST_OK: 37 Python files`.

## Host and opt-in integration observations

```bash
/usr/bin/timeout --signal=KILL 15 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_host.py
```

Observed exit 0:

```json
{"linux": true, "probe_exit_code": 0, "python": "3.11.5", "unshare_path": "/usr/bin/unshare", "user_namespace_probe": "AVAILABLE"}
```

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env MINICTR_LINUX_INTEGRATION=1 +  TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 +  PYTHONPATH=sealed/reference +  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 +  -m unittest sealed.reference_tests.test_linux_integration -v
```

Observed exit 0: `Ran 1 test in 0.344s`, `OK`. This is only the disposable writable-root
`/bin/true` fixture. Read-only remounting, hostile workload containment, alternate
kernels/filesystems, crash recovery, output limits, fuzzing, controlled benchmarking, and transfer
verification were not established in this repair.

## Final archive-boundary audit

The workspace-local test root was empty and removed with the exact command
`find .validation-tmp -mindepth 1 -print; rmdir .validation-tmp`; it exited 0 with no output. A
bounded direct-pack audit was then run:

```bash
/usr/bin/timeout --signal=KILL 30 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json; from pathlib import Path; root=Path("."); prior=root/"PRIOR_BUILD"; pack_top={p.name for p in prior.iterdir()}; prior_entries=list(prior.rglob("*")); pack_entries=[q for name in pack_top for q in ([root/name]+(list((root/name).rglob("*")) if (root/name).is_dir() else []))]; allowed=pack_top|{"PRIOR_BUILD","PRIOR_REVIEW",".agents",".codex",".factory-workspace"}; result={"bytecode_entries":sum(p.name=="__pycache__" or p.suffix==".pyc" for p in pack_entries),"missing_prior_entries":sum(not (root/p.relative_to(prior)).exists() for p in prior_entries),"non_regular_pack_entries":sum(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in pack_entries),"top_level_inventory_roots":sum(p.is_file() and p.suffix==".sha256" for p in root.iterdir()),"unexpected_persistent_top_level_entries":sum(p.name not in allowed and not p.name.startswith(".nfs") for p in root.iterdir())}; print(json.dumps(result,sort_keys=True)); raise SystemExit(1 if any(result.values()) else 0)'
```

Observed exit 0 and exactly:

```json
{"bytecode_entries": 0, "missing_prior_entries": 0, "non_regular_pack_entries": 0, "top_level_inventory_roots": 0, "unexpected_persistent_top_level_entries": 0}
```

The `.nfs` exclusion is limited to transient tombstones created by the execution wrapper on this
NFS workspace; they changed names and disappeared when each command closed. They are not challenge
pack entries. The final packaging verifier separately observed all required files, all forbidden
paths absent, only regular archive entries, exact metadata, and no configured credential pattern.

## Why status remains PARTIAL

The host probe and bounded tests do not make this educational launcher a security boundary.
Cgroups, seccomp, capability minimization, descriptor-pinned filesystem setup, a real init shim,
bounded persistent logs, and production recovery remain absent. No `BUILDS`, `TESTED`, `FUZZED`,
`BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is asserted.
