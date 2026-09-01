# Independent validation record

Review date: 2026-08-31. All candidate access was read-only. Reviewer scratch
space was created outside `CANDIDATE/` and deleted after the checks. Commands
were bounded with `timeout` where they could start processes.

## Environment and toolchains

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
python3 --version
/bin/gcc --version | sed -n '1p'
/usr/bin/unshare --version | sed -n '1p'
```

Observed, all exit 0:

```text
Python 3.11.5
Python 3.6.8
gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
unshare from util-linux 2.32.1
```

The unqualified `python3` is below the candidate's declared Python 3.10
minimum. `git` and `rg` were not available. The system `/tmp` was not writable,
so applicable tests used the reviewer-owned `../.root-review-tmp`; it was
outside the candidate and was removed.

## Deterministic suites

From `CANDIDATE/`, the documented style of command with the default interpreter
was not runnable:

```bash
timeout 30s env TMPDIR=../.root-review-tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -q
```

Observed: exit 1; six test-module import errors. Python 3.6.8 does not support
`from __future__ import annotations`, and it lacks the standard-library
`dataclasses` module.

Using the available supported interpreter:

```bash
timeout 60s env TMPDIR=../.root-review-tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed: exit 0; `Ran 24 tests`; `OK`.

```bash
timeout 90s env TMPDIR=../.root-review-tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed: exit 0; `Ran 65 tests`; `OK`.

```bash
timeout 60s env TMPDIR=../.root-review-tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -q
```

Observed: exit 1; `Ran 24 tests`; `FAILED (errors=32)`. The errors came from the
intentional staged `NotImplementedError` scaffold. This reproduces the builder's
baseline; it is not a completed learner implementation.

```bash
timeout 30s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c \
  'import ast,pathlib; paths=sorted(pathlib.Path("starter").rglob("*.py"))+sorted(pathlib.Path("public_tests").rglob("*.py"))+sorted(pathlib.Path("environment").rglob("*.py"))+sorted(pathlib.Path("sealed/reference").rglob("*.py"))+sorted(pathlib.Path("sealed/reference_tests").rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in paths]; print("parsed", len(paths), "Python files")'
```

Observed: exit 0; `parsed 35 Python files`.

These results reproduce the claimed bundled counts. They do not independently
award a `TESTED` label and do not prove behaviors omitted from those suites.

## Independent state fault injection

The following Python payload was executed as a bounded `python3 -c` command with
`PYTHONPATH=CANDIDATE/sealed/reference`, Python 3.11.5, and reviewer-owned
temporary storage. It replaces only each in-memory store object's sync method;
it does not modify candidate source:

```python
import tempfile
from pathlib import Path
from minibox.errors import StateError
from minibox.state import StateStore

def capture(call):
    try:
        call()
    except StateError as exc:
        return str(exc)

temporary = tempfile.TemporaryDirectory()
base = Path(temporary.name)

transition_store = StateStore(base / "transition", clock=lambda: 1.0)
before = transition_store.create("box")
transition_store._sync_directory = lambda: (_ for _ in ()).throw(
    StateError("injected directory sync failure")
)
transition_error = capture(
    lambda: transition_store.transition("box", "CREATED", "RUNNING")
)
after = transition_store.get("box")

create_store = StateStore(base / "create", clock=lambda: 1.0)
create_store._sync_directory = lambda: (_ for _ in ()).throw(
    StateError("injected directory sync failure")
)
create_error = capture(lambda: create_store.create("new-box"))
created_after_error = create_store.get("new-box")

print({
    "transition_before": (before.status, before.revision),
    "transition_error": transition_error,
    "transition_after": (after.status, after.revision),
    "create_error": create_error,
    "create_after": (created_after_error.status, created_after_error.revision),
})
temporary.cleanup()
```

Observed: exit 0 and:

```text
{'transition_before': ('CREATED', 0), 'transition_error': 'injected directory sync failure', 'transition_after': ('RUNNING', 1), 'create_error': 'injected directory sync failure', 'create_after': ('CREATED', 0)}
```

Both APIs therefore raised after publishing visible state. This contradicts
`REQUIREMENTS.md:226-230` and is not covered by the passing suites.

## Environment probes

From `CANDIDATE/`:

```bash
timeout 10s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/probe.py
timeout 10s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/probe.py --try-userns
```

Both exited 0. The passive report observed Linux
`4.18.0-553.el8_10.x86_64`, x86_64, Python 3.11.5, non-root execution,
`/usr/bin/unshare`, `/usr/bin/true`, all six namespace entries,
`max_user_namespaces=2147483647`, and an absent
`kernel.unprivileged_userns_clone` path. The active report observed
`status="success"`, return code 0, and empty stdout/stderr. This proves only the
narrow user-namespace probe at review time.

The live payload's proc predicate was checked in an ordinary review process:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c \
  'import os; print({"pid":os.getpid(),"proc_self_status_readable":os.access("/proc/self/status",os.R_OK),"proc_self_status_exists":os.path.exists("/proc/self/status")})'
```

Observed: exit 0 and:

```text
{'pid': 2, 'proc_self_status_readable': True, 'proc_self_status_exists': True}
```

Thus readability of `/proc/self/status` alone does not prove a fresh proc view.

## Metadata, artifact, and boundary checks

Both metadata files were strict-parsed as JSON with duplicate keys and
non-finite constants rejected. Observed cross-checks:

```text
manifest keys: independent_validation, productionized, project_id,
  provenance_sha256, schema_version, source_commit, source_id, status,
  validation_labels
project/source IDs match PROVENANCE.json: yes
manifest source_commit matches provenance source commit: yes
manifest provenance_sha256 equals provenance snapshot_sha256: yes
```

File hashes:

```bash
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
```

Observed, exit 0:

```text
61d0f204e6e3a1e7647e3b6eed3a918b3a6b30ede1056213767ed030629a3cdc  CANDIDATE/PROVENANCE.json
cf665f0c237cb6320076e93c64b5419bfcb771e93f61a4054173fca30738ffab  CANDIDATE/MANIFEST.yaml
```

The provenance file hash does not match the manifest's
`f7a36c6e3d6cae8eaefb0e013c4b9f9f9190dc2eb15a90ccdec01284edce28d2`
value. The latter instead repeats the internal `snapshot_sha256` value.

```bash
find CANDIDATE -type f | wc -l
find CANDIDATE -type l | wc -l
find CANDIDATE -not -type d -not -type f -not -type l | wc -l
test -r CANDIDATE/sealed/reference/minibox/state.py
test -r CANDIDATE/sealed/review_exercises/shell-injection/ANSWER.md
```

Observed: 65 regular files, 0 symlinks, 0 special entries, and both sealed-path
readability checks exited 0. A bounded Python scan of all 65 files for private
key headers, AWS/GitHub/OpenAI-like tokens, and assigned password/API-key/access
token literals exited 0 with `credential_pattern_hits: []`.

The candidate-wide aggregate was computed before and after review with:

```bash
find CANDIDATE -type f -print0 | LC_ALL=C sort -z | \
  xargs -0 sha256sum | sha256sum
```

Both observations were:

```text
69ac1ba05023bede977cc32173dae879078cbbdc3c4767b57334336698adc3fa  -
```

No bytecode/cache artifact was found under `CANDIDATE/`.

## C toolchain and live-backend limitation

The first static-build attempt without a reviewer TMPDIR could not create a
compiler temporary file in the immutable candidate and exited 134. Retrying
outside the candidate was bounded:

```bash
test ! -e ../.root-review-tmp/minibox-static-probe && \
timeout 30s env TMPDIR=../.root-review-tmp /bin/gcc \
  -std=c11 -Wall -Wextra -Werror -static -Os -s \
  -o ../.root-review-tmp/minibox-static-probe environment/live_payload.c
```

Observed: exit 1; `gcc: error trying to exec 'cc1': execvp: No such file or
directory`. The compiler frontend is unavailable to this sandbox. The C payload
was not built, so the builder's instrumented dynamic run and earlier linker
failure/success observations are inconclusive here.

A less-informative live backend path could still be checked without compiling
the instrumented payload. A disposable rootfs was prepared outside the
candidate with the benign host `true` binary and its two runtime libraries:

```bash
test ! -e .root-review-live && test ! -e .root-review-tmp && \
mkdir -p .root-review-live/rootfs/bin .root-review-live/rootfs/proc \
  .root-review-live/rootfs/lib64 .root-review-live/state .root-review-tmp && \
cp -L /usr/bin/true .root-review-live/rootfs/bin/true && \
cp -L /lib64/libc.so.6 .root-review-live/rootfs/lib64/libc.so.6 && \
cp -L /lib64/ld-linux-x86-64.so.2 \
  .root-review-live/rootfs/lib64/ld-linux-x86-64.so.2
```

Observed: exit 0. The bounded reference run was:

```bash
timeout 20s env TMPDIR=.root-review-tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=CANDIDATE/sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'from pathlib import Path; from minibox.config import from_dict; from minibox.runtime import LinuxSubprocessBackend,Runtime; from minibox.state import StateStore; rootfs=Path(".root-review-live/rootfs").resolve(); spec=from_dict({"schema_version":1,"rootfs":str(rootfs),"argv":["/bin/true"],"timeout_seconds":5}); store=StateStore(".root-review-live/state"); result=Runtime(store,LinuxSubprocessBackend()).run(spec,"review-true"); state=store.get("review-true"); print({"exit_code":result.exit_code,"stdout":result.stdout,"stderr":result.stderr,"status":state.status,"revision":state.revision})'
```

Observed: exit 0 and:

```text
{'exit_code': 0, 'stdout': b'', 'stderr': b'', 'status': 'EXITED', 'revision': 2}
```

This independently shows that the reference reached its READY/exec path and
completed the lifecycle on this host. Because `true` emits no observations, it
does not verify PID 1, hostname, proc contents, containment, or cleanup against
descendants. Both reviewer scratch directories were then deleted.

## Limitations

- Python 3.10 specifically and non-Linux behavior were not exercised.
- No fuzz campaign, benchmark, transfer run, hostile-workload test, resource
  limit test, security audit, or production qualification was performed.
- The instrumented C live payload could not run because the C toolchain is
  incomplete; only the uninstrumented `true` live smoke was possible.
- `git`, `rg`, network access, and the source repository were unavailable. The
  recorded source commit, upstream license, and no-copy claim were not
  independently authenticated.
- The bundled suites and environment probe are candidate-authored. Independent
  execution makes their observed results evidence, but their scope remains
  limited to the assertions they actually perform.
