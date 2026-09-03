# Validation record — repair generation 3

Observed on 2026-09-02 in the allocated repair workspace. These are builder-side observations, not
independent validation. `MANIFEST.yaml` remains exactly `GENERATED` + `PARTIAL`, requires
independent validation, and keeps `productionized: false`.

## Remediation under test

- Migration `sealed/reference/minictr/migrations/001_fixed_transition_policy.sql` removes the
  legacy writable transition table and installs a trigger whose predicate contains exactly the
  three accepted state pairs. Initialization applies numbered migrations inside its existing
  `BEGIN IMMEDIATE` transaction.
- `validate_rootfs` now rejects non-`Path` inputs with `ValidationError`. Bounded JSON decoding
  and canonicalization translate recursion, oversized-integer, value, and resource failures to
  `ValidationError` before the process factory can be called.
- The documented timestamp profile rejects all optional `:60` spellings deterministically rather
  than treating every date and minute as a possible leap second.
- The direct read-only preflight check is now a regular sealed script. Its replay command contains
  no shell heredoc and therefore does not depend on a writable system temporary directory.

## Toolchain

The configured read-only Python toolchain was invoked by its exact absolute path:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import sys; print(sys.executable); print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3,11) else 1)'
/usr/bin/unshare --version
```

All exited 0. Output was `Python 3.11.5`, then
`/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3` and `3.11.5`, then
`unshare from util-linux 2.32.1`. Python was the only configured language toolchain relevant to
this Python-only pack.

A workspace-local temporary directory was created because system temporary directories are not
assumed writable:

```bash
mkdir .validation-tmp
```

Observed exit 0 with no output.

## Focused repair regressions

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest sealed.reference_tests.test_registry -v
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest sealed.reference_tests.test_spec_and_paths -v
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest sealed.reference_tests.test_runner_and_child -v
```

All exited 0. The modules ran 10, 9, and 6 tests respectively and each reported `OK`.

The registry module first attempted to insert `CREATED -> EXITED` into the removed legacy table,
then attempted the invalid row update; both were rejected and the row remained `CREATED`. A second
test constructed a generation-2-style database containing the rogue transition and verified that
opening it applied schema version 1, removed the policy table, and rejected the same update.
Timestamp cases included the reviewer input `2026-01-02T03:04:60Z`, a historical end-of-month
spelling, and an offset spelling; all produced `ValidationError`.

The path module passed wrong-type cases `"."`, `None`, and `17`, each requiring
`ValidationError`. The runner module supplied 2,000 nested arrays and a 10,000-digit integer to a
runner with a recording process factory; both produced `ValidationError`, and the recorded launch
list remained empty.

## Complete deterministic tests

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed exit 0: 10 tests ran, `OK`.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.checkpoints -v
```

Observed exit 1: four tests ran with one failure and three `NotImplementedError` errors at the
documented untouched-starter stage boundaries. This is the intended initial-red learner state, not
a passing claim.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.checkpoints -v
/usr/bin/timeout --signal=KILL 60 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s adversarial -v
```

All exited 0. Reference checkpoints ran 4 tests and reported `OK`. Sealed discovery ran 42 tests
and reported `OK (skipped=2)`; the two skips were exactly the opt-in Linux smoke tests.
Adversarial discovery ran 4 tests and reported `OK`.

## Host capability and replayable read-only probe

```bash
/usr/bin/timeout --signal=KILL 15 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/check_host.py
```

Observed exit 0:

```json
{"linux": true, "probe_exit_code": 0, "python": "3.11.5", "unshare_path": "/usr/bin/unshare", "user_namespace_probe": "AVAILABLE"}
```

```bash
/usr/bin/timeout --signal=KILL 45 /usr/bin/env MINICTR_LINUX_INTEGRATION=1 TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest sealed.reference_tests.test_linux_integration -v
```

Observed exit 0: both opt-in tests ran and reported `OK` in 0.755 seconds. The disposable writable
rootfs completed preflight and its benign `/bin/true` workload. The default read-only test accepted
only either successful setup or the explicit fail-closed result before workload launch.

The separate setup-only probe uses a persistent script, so Bash does not need temporary storage to
parse the command:

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B sealed/reference_tests/readonly_preflight_probe.py
```

Observed exit 0 and:

```json
{"actionable_unsupported": true, "exit_code": 69, "supported": false, "timed_out": false, "workload_started": false}
```

This host rejected the default read-only remount on workspace storage. The result is evidence of an
actionable, bounded fail-closed path, not evidence that read-only execution succeeded.

## Export boundary and content manifests

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/export_views.py create .validation-export
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/export_views.py verify .validation-export/learner --role learner
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/export_views.py verify .validation-export/instructor --role instructor
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B .validation-export/learner/environment/verify_pack.py
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B .validation-export/instructor/environment/verify_pack.py
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$PWD/.validation-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.validation-export/learner/starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s .validation-export/learner/public_tests -v
```

All exited 0. Creation and explicit verification reported 27 learner payload files and 72
instructor payload files. The view-aware pack verifiers reported 28 learner and 73 instructor
canonical files because each generated view also contains `environment/VIEW_MANIFEST.json`. The
exported learner public suite ran 10 tests and reported `OK`.

The learner manifest SHA-256 was
`5188d9ae990d4a73176a5d0075713d5cbb41a95c59e0fdb7402500325b5570f2`. The instructor
manifest digest is intentionally not embedded: `VALIDATION.md` is instructor payload, so doing so
would create a self-reference. The creation command prints it for external retention.

An independent standard-library recomputation, separate from the pack verifier, was:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import hashlib,json,pathlib,sys; v=pathlib.Path(sys.argv[1]); m=json.loads((v/"environment/VIEW_MANIFEST.json").read_text()); actual={p.relative_to(v).as_posix():(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in v.rglob("*") if p.is_file() and p.relative_to(v).as_posix() != "environment/VIEW_MANIFEST.json"}; declared={x["path"]:(x["size"],x["sha256"]) for x in m["files"]}; dirs=sorted(p.relative_to(v).as_posix() for p in v.rglob("*") if p.is_dir()); print(json.dumps({"actual_files":len(actual),"declared_files":len(declared),"directories_match":dirs==m["directories"],"files_match":actual==declared,"role":m["role"]},sort_keys=True)); raise SystemExit(0 if actual==declared and dirs==m["directories"] else 1)' .validation-export/learner
```

Observed exit 0:

```json
{"actual_files": 27, "declared_files": 27, "directories_match": true, "files_match": true, "role": "learner"}
```

The generated learner top-level allowlist was exactly the nine documented learner roots. Its
verifier found no sealed, reference, evaluator, answer, benchmark, review, or validation payload.

## Syntax, provenance, and source packaging

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import ast,pathlib; roots=(pathlib.Path("starter"),pathlib.Path("public_tests"),pathlib.Path("environment"),pathlib.Path("sealed"),pathlib.Path("adversarial"),pathlib.Path("debugging"),pathlib.Path("review_exercises"),pathlib.Path("benchmarks")); files=sorted(p for root in roots for p in root.rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"),filename=str(p)) for p in files]; print(f"AST_OK: {len(files)} Python files")'
/usr/bin/sha256sum PROVENANCE.json
/usr/bin/sha256sum -c environment/PROVENANCE.sha256
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_pack.py
```

All exited 0. Output was `AST_OK: 43 Python files`, then
`1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611  PROVENANCE.json`,
then `PROVENANCE.json: OK`. The source verifier reported 72 canonical files, complete file set,
forbidden paths absent, regular entries only, exact metadata, and a clean configured credential
scan.

## Final hygiene

After all export and test checks, only the two named scratch trees were removed and the final audits
were run:

```bash
/usr/bin/find .validation-export -depth -delete
/usr/bin/find .validation-tmp -depth -delete
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_pack.py
/usr/bin/timeout --signal=KILL 30 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json; from pathlib import Path; from environment.export_views import INSTRUCTOR_TOP_LEVEL; from environment.verify_pack import FORBIDDEN,REQUIRED; root=Path("."); entries=[p for name in INSTRUCTOR_TOP_LEVEL for p in ([root/name]+(list((root/name).rglob("*")) if (root/name).is_dir() else []))]; allowed=set(INSTRUCTOR_TOP_LEVEL)|{"PRIOR_BUILD","PRIOR_REVIEW",".agents",".codex",".factory-workspace"}; result={"bytecode_entries":sum(p.name=="__pycache__" or p.suffix in {".pyc",".pyo"} for p in entries),"forbidden_paths":sum((root/name).exists() or (root/name).is_symlink() for name in FORBIDDEN),"missing_required_files":sum(not (root/name).is_file() or (root/name).is_symlink() for name in REQUIRED),"non_regular_pack_entries":sum(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in entries),"top_level_inventory_roots":sum(p.is_file() and p.suffix==".sha256" for p in root.iterdir()),"unexpected_persistent_top_level_entries":sum(p.name not in allowed and not p.name.startswith(".nfs") for p in root.iterdir())}; print(json.dumps(result,sort_keys=True)); raise SystemExit(1 if any(result.values()) else 0)'
```

All four exited 0. The source verifier again reported 72 canonical files, complete file set,
forbidden paths absent, regular entries only, exact metadata, and a clean configured credential
scan. The independent structural audit printed:

```json
{"bytecode_entries": 0, "forbidden_paths": 0, "missing_required_files": 0, "non_regular_pack_entries": 0, "top_level_inventory_roots": 0, "unexpected_persistent_top_level_entries": 0}
```

No top-level artifact inventory was created. `PRIOR_BUILD/` and `PRIOR_REVIEW/` remained staged
inputs outside the generated-pack checks.

## Limits and status

The preflight is not a capability reservation; policy or filesystem state can race before the
following launch. The educational runtime still lacks cgroups, seccomp, capability minimization,
descriptor-pinned setup, bounded output storage, a real init shim, crash reconciliation,
hostile-workload validation, fuzzing, controlled benchmarking, transfer verification, and
cross-kernel/filesystem coverage. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is asserted.
