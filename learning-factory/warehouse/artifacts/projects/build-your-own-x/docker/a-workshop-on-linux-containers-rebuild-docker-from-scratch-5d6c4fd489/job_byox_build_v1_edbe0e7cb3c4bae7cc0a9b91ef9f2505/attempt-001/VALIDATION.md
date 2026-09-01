# Validation record

This is worker-observed evidence from 2026-08-31, not independent validation.
The authoritative manifest remains `GENERATED` with labels `GENERATED` and
`PARTIAL`; this record does not award `BUILDS`, `TESTED`, `REVIEWED`, or any
other orchestrator-controlled label.

## Host observation

Both diagnostics were run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 environment/probe.py
PYTHONDONTWRITEBYTECODE=1 python3 environment/probe.py --try-userns
```

Both commands exited 0. The reports observed Linux
`4.18.0-553.el8_10.x86_64`, x86_64, Python 3.11.5, a non-root effective user,
`/bin/unshare`, `/bin/true`, all six `/proc/self/ns` entries, and
`user.max_user_namespaces=2147483647`. The passive report recorded
`not_requested`. The active user-namespace probe recorded `status="success"`,
return code 0, and empty stdout/stderr. The optional
`kernel.unprivileged_userns_clone` path was absent. These facts describe this
one run only.

## Deterministic suites

The final reference commands were:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -v
```

Observed results: the public command exited 0 with 24 tests passing; the
sealed command exited 0 with 65 tests passing. The 89 tests cover the closed
schema, immutable values, path search, traversal and symlink rejection,
namespace-plan argv, durable transitions, corrupt records, a same-state race,
write-failure cleanup, runtime failures, bounded output, timeout cleanup, the
setup/result boundary, and strict child-input parsing. Kernel namespaces are
not entered by these deterministic suites.

The intentionally incomplete learner baseline was also run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter python3 -m unittest discover -s public_tests -q
```

It exited 1 after running 24 tests with `FAILED (errors=32)`. The errors are the
scaffold's staged `NotImplementedError` sites. This is the expected starting
state of the challenge, not a reference failure.

All generated Python was parsed without bytecode output:

```bash
python3 -B -c 'import ast,pathlib; paths=sorted(pathlib.Path("starter").rglob("*.py"))+sorted(pathlib.Path("public_tests").rglob("*.py"))+sorted(pathlib.Path("environment").rglob("*.py"))+sorted(pathlib.Path("sealed/reference").rglob("*.py"))+sorted(pathlib.Path("sealed/reference_tests").rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in paths]; print("parsed", len(paths), "Python files")'
```

It exited 0 and printed `parsed 35 Python files`.

## Optional live namespace smoke test

A fully static validation payload could not be linked on this host:

```bash
test ! -e /tmp/minibox-static-probe && /bin/gcc -std=c11 -Wall -Wextra -Werror -static -Os -s -o /tmp/minibox-static-probe environment/live_payload.c
```

It exited 1 with:

```text
/bin/ld: cannot find -lc
collect2: error: ld returned 1 exit status
```

The unavailable static libc is recorded rather than hidden. For a disposable
host-specific rootfs, the dynamically linked fallback was prepared with:

```bash
test ! -e /tmp/minibox-live-project-884ee11 && mkdir -p /tmp/minibox-live-project-884ee11/rootfs/bin /tmp/minibox-live-project-884ee11/rootfs/proc /tmp/minibox-live-project-884ee11/rootfs/lib64 /tmp/minibox-live-project-884ee11/state && /bin/gcc -std=c11 -Wall -Wextra -Werror -Os -s -o /tmp/minibox-live-project-884ee11/rootfs/bin/live-payload environment/live_payload.c && /bin/cp -L /lib64/libc.so.6 /tmp/minibox-live-project-884ee11/rootfs/lib64/libc.so.6 && /bin/cp -L /lib64/ld-linux-x86-64.so.2 /tmp/minibox-live-project-884ee11/rootfs/lib64/ld-linux-x86-64.so.2
```

That command exited 0 with no output. The final reference backend run was:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -c 'from minibox.config import from_dict; from minibox.runtime import LinuxSubprocessBackend,Runtime; from minibox.state import StateStore; spec=from_dict({"schema_version":1,"rootfs":"/tmp/minibox-live-project-884ee11/rootfs","argv":["/bin/live-payload"],"timeout_seconds":10}); store=StateStore("/tmp/minibox-live-project-884ee11/state"); result=Runtime(store,LinuxSubprocessBackend()).run(spec,"post-review"); state=store.get("post-review"); print({"exit_code":result.exit_code,"stdout":result.stdout.decode("utf-8"),"stderr":result.stderr.decode("utf-8"),"status":state.status,"revision":state.revision})'
```

It exited 0 and printed exactly:

```text
{'exit_code': 17, 'stdout': 'pid=1\nhostname=minibox\nproc=visible\n', 'stderr': '', 'status': 'EXITED', 'revision': 2}
```

Thus this benign run reached the target after namespace/helper setup and saw
PID 1, the configured UTS hostname, and the new proc view. It does not prove
containment against hostile code. The temporary rootfs, copied host libraries,
binary, locks, and state were then removed with:

```bash
find /tmp/minibox-live-project-884ee11 -depth -delete
```

The cleanup exited 0, and both temporary validation paths were confirmed
absent.

## Boundary and artifact checks

The final audit strict-parsed both metadata files as JSON, checked the fixed
manifest object and immutable provenance fields, checked all required paths,
and found no generated forbidden solution path. All generated artifact entries
were regular files or directories; no generated symlink or special file was
found. Factory-injected control entries (`.git`, `.agents`, `.codex`,
`.factory-workspace`, and `JOB.md`) were excluded from artifact scans and were
not modified as challenge content.

This credential-pattern scan was run over generated files:

```bash
rg -n --hidden -g '!.git/**' -g '!.agents/**' -g '!.codex/**' -g '!JOB.md' -g '!.factory-workspace' '(-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|(?i)(password|passwd|api[_-]?key|access[_-]?token)\s*[:=]\s*["'"'][^"'"']+["'"'])' .
```

`rg` exited 1 with no output, meaning no pattern matched. No network access or
upstream content retrieval was attempted.

## Why status remains PARTIAL

The live observation covers one kernel, one util-linux installation, and one
benign payload. There is no independent transfer run, fuzz campaign, benchmark,
security audit, resource-limit test, cgroup implementation, seccomp policy,
capability minimization, descriptor-pinned rootfs, or production review signoff.
The learner starter is deliberately unfinished. Independent validators remain
mandatory.
