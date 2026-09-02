# Independent validation record

Review date: 2026-09-02. Candidate files were treated as immutable. All mutable test data was placed
in a reviewer-owned `.review-tmp` directory beside `CANDIDATE` and removed after testing. Commands
were externally bounded with `/usr/bin/timeout` where they could launch work.

## Environment and tool availability

```bash
/usr/bin/python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
uname -srmo
/usr/bin/unshare --version
stat -f -c 'filesystem=%T block_size=%S' .
```

Observed:

```text
Python 3.6.8
Python 3.11.5
Linux 4.18.0-553.el8_10.x86_64 x86_64 GNU/Linux
unshare from util-linux 2.32.1
filesystem=nfs block_size=32768
```

`rg` and `git` were unavailable (`command not found`), so inventory and static searches used
`find`, `grep`, and `sha256sum`. System temporary directories were not usable in this sandbox. An
initial Python 3.11 run without an explicit `TMPDIR` therefore produced only harness errors:
public `FAILED (errors=4)`, reference `FAILED (errors=16, skipped=1)`, and adversarial
`FAILED (errors=3)`, all rooted in `FileNotFoundError: No usable temporary directory found`.
Those results were treated as inconclusive and rerun with a writable reviewer directory.

The following abbreviations describe the exact paths used below:

```bash
PY311=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
REVIEW_TMP=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_bea6310dcca87b80774536ba77202f0b/attempt-001/.review-tmp
cd /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_bea6310dcca87b80774536ba77202f0b/attempt-001/CANDIDATE
```

## Candidate suites, independently rerun

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$REVIEW_TMP" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter "$PY311" \
  -m unittest discover -s public_tests -v
```

Observed: exit 0, `Ran 10 tests in 0.060s`, `OK`.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$REVIEW_TMP" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference "$PY311" \
  -m unittest discover -s sealed/reference_tests -v
```

Observed: exit 0, `Ran 25 tests in 0.344s`, `OK (skipped=1)`. The skipped case was the explicitly
opt-in Linux integration test.

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env TMPDIR="$REVIEW_TMP" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference "$PY311" \
  -m unittest discover -s adversarial -v
```

Observed: exit 0, `Ran 4 tests in 0.095s`, `OK`.

These are independent observations of candidate-authored suites, not proof by themselves. The
reviewer-owned probes below supplied additional evidence.

## Interpreter reproducibility

```bash
/usr/bin/timeout --signal=KILL 20 /usr/bin/env TMPDIR="$REVIEW_TMP" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /usr/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed: exit 1, `Ran 2 tests`, `FAILED (errors=2)`. Both modules failed while importing
`from __future__ import annotations` under Python 3.6.8. This reproduces the builder's disclosed
toolchain mismatch; it is not counted as a Python 3.11 candidate test failure.

## Host and Linux integration

```bash
/usr/bin/timeout --signal=KILL 15 /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  "$PY311" environment/check_host.py
```

Observed exit 0 and:

```json
{"linux": true, "probe_exit_code": 0, "python": "3.11.5", "unshare_path": "/usr/bin/unshare", "user_namespace_probe": "AVAILABLE"}
```

```bash
/usr/bin/timeout --signal=KILL 30 /usr/bin/env MINICTR_LINUX_INTEGRATION=1 \
  TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PY311" -m unittest sealed/reference_tests/test_linux_integration.py -v
```

Observed: exit 0, `Ran 1 test in 0.411s`, `OK`. This used only the disposable, writable-root
`/bin/true` fixture defined by the test.

A reviewer-owned variant changed only `readonly_root` to `true` while using the same disposable
fixture and the same bounded `build_launch_plan`/`Runner` path. Observed:

```text
timed_out False
exit_code 126
stderr minictr child: PermissionError: [Errno 1] Operation not permitted: '.../root'
```

This independently reproduces the candidate's disclosed read-only-remount limitation on the NFS
workspace; no read-only integration pass is claimed.

## Reviewer-owned behavioral probes

The following bounded inline probe used a barrier and one `Registry` connection per contender,
checked a forbidden direct transition, then used a real sleeping subprocess for the timeout path:

```bash
/usr/bin/timeout --signal=KILL 20 /usr/bin/env TMPDIR="$REVIEW_TMP" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference "$PY311" - <<'PY'
import concurrent.futures
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time

from minictr.errors import TransitionError
from minictr.planner import LaunchPlan
from minictr.registry import Registry
from minictr.runner import Runner
from minictr.spec import ContainerSpec

with tempfile.TemporaryDirectory() as temporary:
    database = Path(temporary) / "state.sqlite3"
    owner = Registry(database)
    owner.create(ContainerSpec.from_mapping({
        "id": "race", "rootfs": "/tmp/root", "command": ["/bin/true"]
    }), "2026-01-01T00:00:00Z")
    barrier = threading.Barrier(2)

    def claim(pid):
        contender = Registry(database)
        try:
            barrier.wait()
            try:
                return "won", contender.claim_start(
                    "race", pid, "2026-01-01T00:00:01Z"
                ).pid
            except TransitionError:
                return "lost", pid
        finally:
            contender.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(claim, (101, 202)))
    print("concurrent_claims", sorted(item[0] for item in outcomes),
          "durable_pid", owner.get("race").pid)
    try:
        owner.connection.execute(
            "UPDATE containers SET state = ? WHERE id = ?", ("CREATED", "race")
        )
    except sqlite3.IntegrityError as exc:
        print("illegal_running_to_created_rejected", str(exc))
    print("durable_state", owner.get("race").state)
    owner.close()

plan = LaunchPlan(
    (sys.executable, "-c", "import time; time.sleep(5)"), (), 0.15
)
started = time.monotonic()
result = Runner().run(plan, b"{}")
print("real_timeout", result.timed_out, result.exit_code,
      "elapsed_lt_2s", time.monotonic() - started < 2.0)
PY
```

Observed:

```text
concurrent_claims ['lost', 'won'] durable_pid 202
illegal_running_to_created_rejected invalid container state transition
durable_state RUNNING
real_timeout True -9 elapsed_lt_2s True
```

The winning PID is scheduling-dependent; the one-winner/one-loser invariant is the assertion. An
earlier exploratory probe used `RUNNING -> FAILED`, observed that it was accepted, and was discarded
because that transition is expressly legal under R4.

### RFC-3339 negative probe

Using the public `Registry.create` method, the reviewer attempted three timestamps that
`datetime.fromisoformat` accepts but RFC 3339 does not:

```bash
/usr/bin/timeout --signal=KILL 10 /usr/bin/env TMPDIR="$REVIEW_TMP" \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference "$PY311" - <<'PY'
import json
from pathlib import Path
import tempfile
from minictr.registry import Registry
from minictr.spec import ContainerSpec

candidates = (
    "2026-W01-1T03:04:05+00:00",
    "20260102T030405+00:00",
    "2026-01-02Q03:04:05+00:00",
)
accepted = []
with tempfile.TemporaryDirectory() as temporary:
    registry = Registry(Path(temporary) / "timestamps.sqlite3")
    for index, timestamp in enumerate(candidates):
        spec = ContainerSpec.from_mapping({
            "id": "t" + str(index),
            "rootfs": "/tmp/root",
            "command": ["/bin/true"],
        })
        try:
            registry.create(spec, timestamp)
        except Exception:
            pass
        else:
            accepted.append(timestamp)
    registry.close()
print("non_rfc_timestamps_accepted", json.dumps(accepted))
PY
```

Inputs:

```text
2026-W01-1T03:04:05+00:00
20260102T030405+00:00
2026-01-02Q03:04:05+00:00
```

Observed:

```text
non_rfc_timestamps_accepted ["2026-W01-1T03:04:05+00:00", "20260102T030405+00:00", "2026-01-02Q03:04:05+00:00"]
```

All three rows were committed successfully. This is the correctness basis for the `REVISE`
verdict.

## Metadata, provenance, packaging, and hygiene

```bash
"$PY311" environment/verify_pack.py
```

Observed exit 0:

```text
OK: 23 required files; forbidden paths absent; regular entries only; metadata and credential scan clean
```

An independent strict-JSON and identity comparison observed:

```text
manifest_labels ['GENERATED', 'PARTIAL']
productionized False
identity_match True True True
snapshot_field_match True
provenance_file_sha256 1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611
declared_provenance_sha256 f7190ea0b5ce4b06359e84384b56d25ad265a0faf0bfdd6208378b4a17b5ca5a
```

Thus the metadata identities and declared snapshot field are internally consistent, while the
manifest field named `provenance_sha256` is not the content digest of `PROVENANCE.json`.

```bash
"$PY311" -B -c 'import ast,pathlib; files=sorted(pathlib.Path(".").rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in files]; print(f"AST_OK: {len(files)} Python files")'
find . -type l -o -type b -o -type c -o -type p -o -type s
find . -type d -name __pycache__ -o -type f -name '*.pyc'
```

Observed: `AST_OK: 35 Python files`; both `find` commands produced no candidate entries. A separate
SHA-256 inventory was captured with `find ... -print0 | sort -z | xargs -0 sha256sum`.

## Staged-exercise behavior

```bash
cd debugging/path_escape
/usr/bin/timeout --signal=KILL 20 /usr/bin/env TMPDIR="$REVIEW_TMP" \
  PYTHONDONTWRITEBYTECODE=1 "$PY311" -m unittest test_candidate.py -v
```

Observed: exit 1, `Ran 2 tests`, `FAILED (failures=2)`, with both expected `ValueError not raised`
assertions. This is the advertised reproducer against deliberately vulnerable exercise code, not a
failure of the sealed correction.

## Inconclusive or unavailable checks

- The upstream immutable catalog snapshot and linked tutorial were not supplied, and network access
  was unavailable. No originality comparison or external license confirmation was possible.
- No rendered student view or view-generation command was supplied. Static placement was reviewed,
  but sealed-content exclusion requires separate orchestrator evidence.
- The exploratory benchmark was not rerun as acceptance evidence because no `BENCHMARKED` label is
  claimed and its own methodology explicitly disallows that inference.
- Fuzzing, hostile workloads, output-exhaustion behavior, crash/power-loss recovery, alternate
  kernels/filesystems, transfer verification, and production controls were not tested.
