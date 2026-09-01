# Repair-generation validation record

Status remains **GENERATED + PARTIAL**. Independent validation is required. These observations were made in the repair workspace on 2026-08-31 and do not assign `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

The shell emitted UID/GID lookup warnings before many commands. Those environment warnings are omitted from repeated excerpts below; they did not change the recorded command exits.

## Deterministic pack audit

From the pack root:

```bash
python3 -B sealed/validation/check_pack.py
```

Final observed exit: `0`.

```text
PASS required files present: 23
PASS forbidden paths absent: 21
PASS exact pack top level: 17
PASS regular files: 60; nonempty directories: 24
PASS immutable JSON, source-snapshot hash, and GENERATED/PARTIAL labels match
PASS machine-readable learner-view allowlist and runtime boundary match
PASS harness-controlled learner suite content lock: a3f62d3b7370066dc4e7d7aa6f9c563cad5614fcc27a573e817ded056c90b032
PASS no credential-like patterns in generated files: 60
PASS challenge-pack-content-v1 SHA-256 excluding VALIDATION.md: bf0169e1460a16d677e1776e223047297771e202e9f2155e7f20ed6032692e80 (59 files)
```

`challenge-pack-content-v1` hashes a domain separator followed by length-prefixed UTF-8 relative paths and length-prefixed file bytes in path order. It excludes only `VALIDATION.md` to avoid self-reference. Empty directories are rejected, so every archived directory is implied by a hashed file path; directory-only transfer differences cannot be hidden by this digest. The factory/orchestrator must still own and compare the final whole-artifact `tree-sha256-v2` digest outside the archive before granting transfer verification.

The following strict-JSON parses each exited `0`; no parser diagnostic was observed:

```bash
python3 -m json.tool MANIFEST.yaml
python3 -m json.tool PROVENANCE.json
python3 -m json.tool environment/learner-view.json
```

Raw immutable-file verification:

```bash
sha256sum MANIFEST.yaml PROVENANCE.json
```

Exit `0`:

```text
ea4d7db5b05bd6edfd2a9e85831707e7f4d79299cafd59c49e1a93feb931626c  MANIFEST.yaml
0ef563654487305f40e29ea6aade9bcce1477b623409b1038a95848b2f995b4d  PROVENANCE.json
```

The checker also reproduced `89405d3e84a08d0e0a7a1b67b4b82b38255f0e1fa7e888ed79ca53227da8d60e` from the canonical object containing exactly `PROVENANCE.json`'s `project` and `source` members and matched it to both immutable snapshot fields. `LICENSE_BOUNDARY.md` documents that preimage and distinguishes it from the raw and complete-canonical file digests.

## Learner-view code and Python checks

No actual student workspace was created. The view tests use synthetic temporary fixture content under a bounded scratch directory, and the scratch directory was empty and removed afterward.

```bash
TMPDIR="$PWD/sealed/validation/test-scratch" python3 -B -m unittest discover -s sealed/validation -p 'test_*.py' -v
```

Exit `0`:

```text
test_destination_inside_source_is_rejected (test_learner_view.LearnerViewTests) ... ok
test_existing_destination_is_never_overwritten (test_learner_view.LearnerViewTests) ... ok
test_isolation_command_mounts_only_allowlisted_entries (test_learner_view.LearnerViewTests) ... ok
test_materialize_copies_only_allowlist (test_learner_view.LearnerViewTests) ... ok
test_special_source_entry_is_rejected (test_learner_view.LearnerViewTests) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.564s

OK
```

All Python validator sources were parsed without importing them or creating bytecode:

```bash
python3 -B -c "import ast, pathlib; files=sorted(pathlib.Path('sealed/validation').glob('*.py')); [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in files]; print('PASS parsed {} Python validation files'.format(len(files)))"
```

Exit `0`:

```text
PASS parsed 5 Python validation files
```

The sealed suite lock and seeded-mutation anchors were checked without creating candidate modules:

```bash
python3 -B -c "import runpy; values=runpy.run_path('sealed/validation/run_learner_validation.py'); print('PASS suite content lock: {}'.format(values['verify_locked_inputs']()))"
```

Exit `0`:

```text
PASS suite content lock: a3f62d3b7370066dc4e7d7aa6f9c563cad5614fcc27a573e817ded056c90b032
```

```bash
python3 -B -c "import pathlib,runpy; v=runpy.run_path('sealed/validation/run_learner_validation.py'); root=pathlib.Path('sealed/reference'); counts={name:(root/spec[0]).read_text(encoding='utf-8').count(spec[1]) for name,spec in v['MUTATIONS'].items()}; print(counts); assert all(value == 1 for value in counts.values()); print('PASS all seeded-defect anchors are unique')"
```

Exit `0`:

```text
{'forged-coordinate-accepted': 1, 'negative-slot-accepted': 1, 'unchecked-add': 1}
PASS all seeded-defect anchors are unique
```

## Go toolchain blocker

```bash
command -v go gofmt gccgo tinygo gotip gopls goimports
```

Exit `1` with no tool path printed.

```bash
go version
```

Exit `127`:

```text
/bin/bash: go: command not found
```

Each module command below was attempted once and exited `127` with `/bin/bash: go: command not found`:

| Working directory | Exact command |
| --- | --- |
| `starter/` | `GOTOOLCHAIN=local go test ./...` |
| `public_tests/` | `GOTOOLCHAIN=local go test ./...` |
| `sealed/reference/` | `GOTOOLCHAIN=local go test ./...` |
| `sealed/reference_tests/` | `GOTOOLCHAIN=local go test ./...` |

The candidate-harness self-check was also attempted:

```bash
python3 -B sealed/validation/run_learner_validation.py --self-check
```

Exit `2`:

```text
BLOCKED Go executable not found
```

Consequently no Go source was compiled or formatted, and the harness could not yet demonstrate that the completed reference passes candidate-local plus pristine public plus sealed learner-targeted tests or that all three seeded bad implementations are rejected. The suite, immutable-content lock, generated replacement logic, offline environment, bounded process-group execution, reference materialization, and mutations are reproducible inputs for an independent Go-equipped validator; their presence is not pass evidence.

## Process-isolation blocker

```bash
bwrap --version
```

Exit `0`:

```text
bubblewrap 0.4.0
```

An initial smoke command used `--clearenv`:

```bash
bwrap --unshare-all --die-with-parent --new-session --clearenv --ro-bind /usr /usr --ro-bind /lib64 /lib64 --proc /proc --dev /dev /usr/bin/python3 -c 'print("PASS bubblewrap subprocess")'
```

It exited `1` with `bwrap: Unknown option --clearenv`. The validator was repaired to pass a minimal environment directly to `subprocess.Popen` and no longer emits that option.

A second smoke command used only options supported by 0.4.0:

```bash
bwrap --unshare-all --die-with-parent --new-session --ro-bind /usr /usr --ro-bind /lib64 /lib64 --proc /proc --dev /dev /usr/bin/python3 -c 'print("PASS bubblewrap subprocess")'
```

Exit `1`:

```text
bwrap: loopback: Failed to create NETLINK_ROUTE socket: Operation not permitted
```

A diagnostic retry was:

```bash
bwrap --unshare-all --share-net --die-with-parent --new-session --ro-bind /usr /usr --ro-bind /lib64 /lib64 --proc /proc --dev /dev /usr/bin/python3 -c 'print("PASS bubblewrap subprocess")'
```

It also exited `1`, with `bwrap: Failed to mount tmpfs: No such file or directory`. Thus the executable is present but nested namespace/mount creation is blocked in this worker sandbox. The actual final-pack isolation probe was not run, and no learner view was materialized. A fresh controller environment must run `validate_student_view.py` and observe the sealed-path read failures before treating the disclosure boundary as enforced.

## Prior-pack preservation

This read-only check compared every prior entry's relative path with the repaired top level:

```bash
python3 -B -c "from pathlib import Path; source=Path('PRIOR_BUILD'); missing=[str(path.relative_to(source)) for path in source.rglob('*') if not (Path('.')/path.relative_to(source)).exists()]; print('prior_entries_missing={}'.format(missing)); raise SystemExit(bool(missing))"
```

Exit `0`:

```text
prior_entries_missing=[]
```

`find PRIOR_BUILD PRIOR_REVIEW -perm /222 -print` exited `0` with no output. Neither staged root was made writable or used as an output location.

## Not performed and required next evidence

- Go compilation, formatting, unit/public/sealed test execution, race detection, fuzzing, or benchmarks
- completed-reference acceptance and seeded-bad rejection by the Go harness
- an actual learner-view materialization or learner-process sealed-read probe
- final archive collection or external `tree-sha256-v2` comparison
- upstream/network comparison, transfer verification, independent review, or production hardening

These blockers and omissions are why the immutable manifest remains `GENERATED` with labels exactly `GENERATED`, `PARTIAL`.
