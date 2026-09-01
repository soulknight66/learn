# Validation record

This is fresh worker-observed repair evidence from 2026-08-31. It is not
independent validation. The authoritative manifest remains `GENERATED` with
labels `GENERATED` and `PARTIAL`; no `BUILDS`, `TESTED`, `REVIEWED`,
`TRANSFER_VERIFIED`, `PRODUCTIONIZED`, or other controller-owned label is
claimed.

All commands below ran from the pack root. Commands that can create processes
used `timeout`; Python commands used `PYTHONDONTWRITEBYTECODE=1`. Temporary test
storage was the explicitly created `sealed/.repair-validation-tmp`, and it was
removed after the test processes ended. No learner workspace or learner
archive was written: the learner-view check constructed its tar stream only in
memory.

## Interpreter observations

```bash
python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Both exited 0 and printed, respectively:

```text
Python 3.6.8
Python 3.11.5
```

The default interpreter is below the documented Python 3.10 minimum, so all
Python validation used the explicit Python 3.11.5 path.

## Deterministic suites

```bash
timeout 90s env TMPDIR=sealed/.repair-validation-tmp \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed: exit 0; `Ran 24 tests`; `OK`.

```bash
timeout 120s env TMPDIR=sealed/.repair-validation-tmp \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed on the final run: exit 0; `Ran 73 tests`; `OK`. The suite includes
new regressions for create and transition directory-sync failures, recovery,
wrong-store recovery, interruption during post-publication sync, deterministic
learner packaging, artifact inventory, and the pack audit.

An earlier informative attempt used a top-level scratch directory:

```bash
timeout 120s env TMPDIR=.repair-validation-tmp \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

That interim run exited 1 with one error because the inventory control rejected
the unknown top-level `.repair-validation-tmp` entry. Scratch was moved below
the excluded `sealed/` production area, and the final command above passed.
This shows the unknown-root rejection operating as designed; it was not hidden
as a product success.

The intentionally incomplete learner baseline was run with:

```bash
timeout 90s env TMPDIR=sealed/.repair-validation-tmp \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -q
```

Observed: exit 1; `Ran 24 tests`; `FAILED (errors=32)`. The errors are the
staged `NotImplementedError` scaffold, not a completed learner implementation.

All generated Python sources were parsed without imports or bytecode output:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c \
  'import ast,pathlib; roots=("starter","public_tests","environment","sealed"); paths=sorted(p for root in roots for p in pathlib.Path(root).rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in paths]; print("parsed",len(paths),"Python files")'
```

Observed: exit 0; `parsed 39 Python files`.

## Post-publication state fault injection

In addition to the unit regressions, the prior review's transition fault shape
was reproduced against the repaired reference:

```bash
timeout 30s env TMPDIR=sealed/.repair-validation-tmp \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import tempfile; from pathlib import Path; from minibox.errors import StateCommitUncertain,StateError; from minibox.state import StateStore; temporary=tempfile.TemporaryDirectory(); base=Path(temporary.name); store=StateStore(base/"states",clock=lambda:1.0); store.create("box"); original=store._sync_directory; store._sync_directory=lambda: (_ for _ in ()).throw(StateError("injected directory sync failure")); caught=None
try:
 store.transition("box","CREATED","RUNNING")
except StateCommitUncertain as exc:
 caught=exc
finally:
 store._sync_directory=original
visible=store.get("box"); recovered=store.recover(caught); print({"exception":type(caught).__name__,"proposed":(caught.proposed_state.status,caught.proposed_state.revision),"visible":(visible.status,visible.revision),"recovered":(recovered.status,recovered.revision)}); temporary.cleanup()'
```

Observed: exit 0 and:

```text
{'exception': 'StateCommitUncertain', 'proposed': ('RUNNING', 1), 'visible': ('RUNNING', 1), 'recovered': ('RUNNING', 1)}
```

The repaired API therefore does not report this as an ordinary failed
transition. It exposes the exact visible proposal and requires explicit
read/compare/re-sync recovery. This is still not a crash-recovery controller;
durable intent is a documented production requirement.

## Learner-view and pack integrity controls

The final quiescent learner-view check was:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/production/learner_view.py --source .
```

Observed: exit 0 and:

```text
{"archive_bytes":102400,"archive_sha256":"e198d10e8dd43ee7364251338a8540c3a67629aac3061fd08d4175f5e6d3b849","entries":31,"manifest_sha256":"cf665f0c237cb6320076e93c64b5419bfcb771e93f61a4054173fca30738ffab","project_id":"project_884ee11fc61abc48b60825556299dae5","sealed_entries_selected":0,"sealed_source_entries_scanned":51}
```

The strict policy is checked against constants independently embedded in the
packager. The in-memory ustar stream is deterministic, includes only the nine
authorized learner roots, and selected zero of the 51 source entries at or
below `sealed/`. No archive was left in the workspace.

The quiescent pack audit command is:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/production/audit_pack.py --root .
```

Observed after final inventory generation: exit 0. It checked 71 inventoried
regular files, strict-parsed both metadata documents, found every required
path, found no forbidden path, found no credential-pattern hit, selected zero
sealed learner entries, and confirmed status `GENERATED` with labels
`["GENERATED","PARTIAL"]`. It also confirmed these immutable byte hashes:

```text
MANIFEST.yaml   cf665f0c237cb6320076e93c64b5419bfcb771e93f61a4054173fca30738ffab
PROVENANCE.json 61d0f204e6e3a1e7647e3b6eed3a918b3a6b30ede1056213767ed030629a3cdc
```

One audit attempt was mistakenly launched concurrently with the sealed suite.
It exited 1 after a test temporary file disappeared between inventory listing
and reading. The identical audit command was rerun serially after all test
processes ended and exited 0. Inventory and release checks require a quiescent
source tree.

The inventory was finalized and then verified with:

```bash
env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/production/artifact_inventory.py write --root .
timeout 30s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/production/artifact_inventory.py verify --root .
```

Observed: both exited 0 and reported 71 entries with the same inventory-file
SHA-256. The digest is not duplicated in this file because the inventory hashes
this validation record; embedding it here would change it recursively. The
final digest is independently observable by hashing
`sealed/production/ARTIFACT_INVENTORY.json`. The inventory excludes only its
own output and explicitly records that exclusion. It is tied to the actual
manifest bytes, actual provenance-document bytes, and immutable provenance
snapshot id, but the immutable manifest cannot point back to it; a release
service must hash or sign the inventory before transfer.

## Environment and C-toolchain observations

```bash
timeout 15s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/probe.py
timeout 15s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/probe.py --try-userns
```

Both exited 0. They observed Linux `4.18.0-553.el8_10.x86_64`, x86_64,
Python 3.11.5, non-root execution, `/usr/bin/unshare`, `/usr/bin/true`, all six
namespace entries and identities, and
`user.max_user_namespaces=2147483647`. The passive status was `not_requested`.
The active narrow user-namespace probe reported `success`, return code 0, and
empty stdout/stderr. The optional `kernel.unprivileged_userns_clone` path was
absent. Each command ran in its own harness process, so namespace inode values
from the two reports are not treated as one stable host baseline.

The enhanced benign C payload was compiled only to an object, with a bounded
command:

```bash
timeout 30s env TMPDIR=sealed/.repair-validation-tmp /bin/gcc \
  -std=c11 -Wall -Wextra -Werror -c \
  -o sealed/.repair-validation-tmp/live_payload.o environment/live_payload.c
```

Observed: exit 1 and:

```text
gcc: error trying to exec 'cc1': execvp: No such file or directory
```

The compiler frontend is unavailable in this sandbox. No object, executable,
rootfs, or fresh live-backend result was produced. The revised source reports
namespace identities, procfs mount metadata, and visible numeric PIDs, but this
worker makes no claim that it compiled or proved a fresh proc view.

## Prior-pack preservation and staged evidence

The following bounded check compared every staged prior-build entry's relative
path and filesystem kind with the repaired top-level pack. It also computed
content/path evidence digests for both immutable staged roots:

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c \
  'import hashlib,json,os,pathlib,stat

def digest(root):
 root=pathlib.Path(root); h=hashlib.sha256(); count=0
 for path in sorted(root.rglob("*"),key=lambda p:p.relative_to(root).as_posix()):
  rel=path.relative_to(root).as_posix(); mode=os.lstat(path).st_mode
  kind="d" if stat.S_ISDIR(mode) else "f" if stat.S_ISREG(mode) else "x"
  h.update(kind.encode()+b"\0"+rel.encode()+b"\0")
  if kind=="f": h.update(hashlib.sha256(path.read_bytes()).digest()); count+=1
  elif kind=="x": raise SystemExit("unsupported staged entry "+rel)
 return {"regular_files":count,"tree_evidence_sha256":h.hexdigest()}
prior=pathlib.Path("PRIOR_BUILD"); missing=[]; wrong=[]; entries=0
for path in sorted(prior.rglob("*")):
 rel=path.relative_to(prior); target=pathlib.Path(rel); entries+=1
 if not target.exists(): missing.append(rel.as_posix())
 elif path.is_file()!=target.is_file() or path.is_dir()!=target.is_dir(): wrong.append(rel.as_posix())
print(json.dumps({"prior_entries_checked":entries,"prior_entries_missing":missing,"prior_entry_type_mismatches":wrong,"staged":{"PRIOR_BUILD":digest("PRIOR_BUILD"),"PRIOR_REVIEW":digest("PRIOR_REVIEW")}},sort_keys=True))'
```

Observed twice, before and after finalization: exit 0 with 87 prior entries
checked, no missing entry, no type mismatch, and:

```text
PRIOR_BUILD  65 files  7d1cb21fdbd9695656cbc063627c777dcaaba63ca4b4d38177d4740c5c80556a
PRIOR_REVIEW  3 files  61fbf0c81f122114ed887a874bd3de5f3597a05e24c943a45213590dd81982e9
```

These are locally defined evidence digests, not claims to reproduce the
controller's `tree-sha256-v2` algorithm. Both staged roots remained untouched.
The pack audit also rejected symlinks and special files in generated pack
roots. No bytecode/cache artifact remained.

## Why status remains PARTIAL

- The learner starter is intentionally unfinished.
- The C frontend was unavailable, so the revised live probe did not compile or
  run and no fresh end-to-end namespace comparison was made.
- Python 3.10 specifically, non-Linux portability, hostile workloads, fuzzing,
  benchmarking, resource exhaustion, crash/restart reconciliation, transfer
  verification, and production/security qualification were not tested.
- The source commit and no-copy assertion were not authenticated against the
  upstream network resource; no network access was attempted.
- The learner-view and inventory controls require independent release-service
  enforcement and an external signature or trusted hash.

Passing deterministic bundled tests establishes only their asserted behavior.
Independent validators remain mandatory.
