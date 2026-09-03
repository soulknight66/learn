# Validation record — repair generation 2

Observed on 2026-09-02 in the allocated repair workspace. These are builder-side observations, not
independent validation. `MANIFEST.yaml` remains exactly `GENERATED` + `PARTIAL`, requires independent
validation, and keeps `productionized: false`.

## Toolchain

The configured read-only Python toolchain was invoked by its exact absolute path:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import sys; print(sys.executable); print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3,11) else 1)'
/usr/bin/unshare --version
```

All exited 0. Output was `Python 3.11.5`, then the exact configured executable path and `3.11.5`,
then `unshare from util-linux 2.32.1`. No other configured language toolchain was needed for this
Python-only pack.

A clean workspace-local temporary directory was used because system temporary directories are not
assumed writable:

```bash
mkdir .validation-tmp
```

Observed exit 0 with no output.

## Deterministic tests

Every command below is recorded without transcript separator tokens and is directly replayable from
the pack root.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed exit 0: 10 tests ran, `OK`.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.checkpoints -v
```

Observed exit 1: 4 tests ran with one failure and three errors at the documented untouched-starter
TODO boundaries. This is an intentional initial-red learner signal, not a passing claim.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.checkpoints -v
```

Observed exit 0: 4 tests ran, `OK`.

```bash
/usr/bin/timeout --signal=KILL 60 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```

Observed exit 0: 38 tests ran, `OK (skipped=2)`. The two skips were exactly the opt-in Linux tests.
The suite includes export separation/integrity, setup-only preflight, no-workload-on-preflight-
failure, complete verifier inventory, registry transactions, process supervision, and path/spec
tests.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s adversarial -v
```

Observed exit 0: 4 tests ran, `OK`.

## Export boundary and content manifests

The complete pack was verified, then exported into a new scratch destination and both views were
independently re-read:

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_pack.py
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/export_views.py create .validation-export
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/export_views.py verify .validation-export/learner --role learner
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B .validation-export/learner/environment/verify_pack.py
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B .validation-export/instructor/environment/verify_pack.py
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.validation-export/learner/starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s .validation-export/learner/public_tests -v
```

All six exited 0; the exported learner suite ran 10 tests and reported `OK`. The source verifier
reported 70 canonical files. Creation reported 27 learner
payload files and 70 instructor payload files; explicit learner verification repeated 27. The
view-aware pack verifiers reported 28 learner files and 71 instructor files because each count also
includes its generated `environment/VIEW_MANIFEST.json`. Creation printed the SHA-256 of each view
manifest for external retention. The instructor digest is intentionally not copied into this source
record: this `VALIDATION.md` is itself instructor payload, so embedding that digest would create a
self-reference. Each generated manifest covers every other file by path, byte size, and SHA-256 and
covers every directory; its printed digest binds the manifest itself.

```bash
/usr/bin/find .validation-export/learner -maxdepth 1 -mindepth 1 -printf '%f\n' | /usr/bin/sort
/usr/bin/find .validation-export/learner -type d \( -name sealed -o -name adversarial -o -name debugging -o -name review_exercises -o -name benchmarks -o -name reference -o -name reference_tests -o -name hidden_tests -o -name solution -o -name solutions -o -name answers \) -print
```

Both exited 0. The first printed exactly `AGENTS.md`, `CONCEPTS.md`, `DESIGN_QUESTIONS.md`,
`MANIFEST.yaml`, `README.md`, `REQUIREMENTS.md`, `environment`, `public_tests`, and `starter` in
sorted order. The second produced no output. Unit tests also changed a manifested learner file and
added an instructor file; both altered views were rejected.

## Host capability and read-only default

```bash
/usr/bin/timeout --signal=KILL 15 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/check_host.py
```

Observed exit 0 and:

```json
{"linux": true, "probe_exit_code": 0, "python": "3.11.5", "unshare_path": "/usr/bin/unshare", "user_namespace_probe": "AVAILABLE"}
```

The opt-in tests exercise a writable disposable `/bin/true` root through preflight and workload,
and the default read-only root through preflight before any possible workload:

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env MINICTR_LINUX_INTEGRATION=1 TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest sealed.reference_tests.test_linux_integration -v
```

Observed exit 0: 2 tests ran, `OK`. A separate direct default-mode probe used the same disposable
rootfs fixture and called only `build_preflight_plan` plus `Runner.run`:

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import json
from pathlib import Path
import shutil
import tempfile
from minictr.planner import build_preflight_plan
from minictr.runner import Runner
from minictr.spec import ContainerSpec

dependencies = (Path('/bin/true'), Path('/lib64/libc.so.6'), Path('/lib64/ld-linux-x86-64.so.2'))
with tempfile.TemporaryDirectory(dir=Path('.validation-tmp')) as temporary:
    root = Path(temporary) / 'root'
    (root / 'bin').mkdir(parents=True)
    (root / 'lib64').mkdir()
    (root / 'proc').mkdir()
    for source, target in zip(dependencies, ('bin/true', 'lib64/libc.so.6', 'lib64/ld-linux-x86-64.so.2')):
        shutil.copy2(source, root / target)
    spec = ContainerSpec.from_mapping({
        'id': 'readonly', 'rootfs': str(root.resolve()), 'command': ['/bin/true'],
        'timeout_seconds': 10, 'network': False,
    })
    payload = json.dumps(spec.to_mapping(), sort_keys=True, separators=(',', ':')).encode()
    result = Runner().run(build_preflight_plan(spec, '/usr/bin/unshare'), payload)
    report = {
        'exit_code': result.exit_code,
        'stderr': result.stderr.decode(errors='replace').strip(),
        'timed_out': result.timed_out,
        'workload_started': False,
    }
    print(json.dumps(report, sort_keys=True))
    supported = result.exit_code == 0 and not result.timed_out
    actionable = result.exit_code == 69 and not result.timed_out and 'UNSUPPORTED read-only root setup' in report['stderr']
    raise SystemExit(0 if supported or actionable else 1)
PY
```

Observed probe exit 0. The supervised preflight returned exit 69 without timeout and reported
`UNSUPPORTED read-only root setup: PermissionError: [Errno 1] Operation not permitted`, followed by
`the workload was not started` and the explicit disposable-rootfs fallback. This host therefore
still cannot establish the safe default on its NFS-backed scratch root, but it now rejects that host
capability before workload exec instead of failing only after launch. The unit CLI test separately
asserted that this preflight result causes exactly one runner call, not a workload call.

## Syntax, provenance, and final hygiene

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import ast,pathlib; roots=(pathlib.Path("starter"),pathlib.Path("public_tests"),pathlib.Path("environment"),pathlib.Path("sealed"),pathlib.Path("adversarial"),pathlib.Path("debugging"),pathlib.Path("review_exercises"),pathlib.Path("benchmarks")); files=sorted(p for root in roots for p in root.rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"),filename=str(p)) for p in files]; print(f"AST_OK: {len(files)} Python files")'
/usr/bin/sha256sum PROVENANCE.json
/usr/bin/sha256sum -c environment/PROVENANCE.sha256
```

All exited 0. Output was `AST_OK: 42 Python files`, then
`1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611  PROVENANCE.json`, then
`PROVENANCE.json: OK`.

After the export and test scratch products were explicitly removed, the pack audit was run:

```bash
/usr/bin/find .validation-export -depth -delete
/usr/bin/find .validation-tmp -depth -delete
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_pack.py
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json,stat; from pathlib import Path; from environment.export_views import INSTRUCTOR_TOP_LEVEL; from environment.verify_pack import FORBIDDEN,REQUIRED; root=Path("."); entries=[p for name in INSTRUCTOR_TOP_LEVEL for p in ([root/name]+(list((root/name).rglob("*")) if (root/name).is_dir() else []))]; allowed=set(INSTRUCTOR_TOP_LEVEL)|{"PRIOR_BUILD","PRIOR_REVIEW",".agents",".codex",".factory-workspace"}; result={"bytecode_entries":sum(p.name=="__pycache__" or p.suffix in {".pyc",".pyo"} for p in entries),"forbidden_paths":sum((root/name).exists() or (root/name).is_symlink() for name in FORBIDDEN),"missing_required_files":sum(not (root/name).is_file() or (root/name).is_symlink() for name in REQUIRED),"non_regular_pack_entries":sum(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in entries),"top_level_inventory_roots":sum(p.is_file() and p.suffix==".sha256" for p in root.iterdir()),"unexpected_persistent_top_level_entries":sum(p.name not in allowed and not p.name.startswith(".nfs") for p in root.iterdir())}; print(json.dumps(result,sort_keys=True)); raise SystemExit(1 if any(result.values()) else 0)'
```

All four exited 0. The verifier reported the complete 70-file source set, forbidden paths absent,
regular entries only, exact metadata, and a clean configured credential scan. The final audit
printed:

```json
{"bytecode_entries": 0, "forbidden_paths": 0, "missing_required_files": 0, "non_regular_pack_entries": 0, "top_level_inventory_roots": 0, "unexpected_persistent_top_level_entries": 0}
```

No top-level artifact inventory was created. `PRIOR_BUILD/` and `PRIOR_REVIEW/` remained staged
read-only inputs and were excluded from generated-pack checks.

## Limits and status

The preflight is not a capability reservation; policy or filesystem state can race before the
following launch. The educational runtime still lacks cgroups, seccomp, capability minimization,
descriptor-pinned setup, bounded output storage, a real init shim, crash reconciliation, hostile-
workload validation, fuzzing, controlled benchmarking, transfer verification, and cross-kernel/
filesystem coverage. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is asserted.
