# Validation record

Observed on 2026-09-02 in the allocated build workspace. These are generator-side observations, not
independent validation. `MANIFEST.yaml` intentionally remains `GENERATED` + `PARTIAL` with
`productionized: false`.

## Toolchain discovery and informative failed attempt

The first documented-style invocations used the default `python3`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -v
```

Observed: the public discovery ended `FAILED (errors=2)` and sealed discovery ended
`FAILED (errors=4)`. Imports reported `SyntaxError: future feature annotations is not defined`; one
3.11 test also used parenthesized context managers. A later direct check printed `Python 3.6.8` for
`/usr/bin/python3`. This is a toolchain mismatch, not recorded as a passing build.

The provided toolchain was then selected explicitly:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed: `Python 3.11.5`.

## Deterministic tests

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed final run: `Ran 10 tests in 0.082s`, `OK`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed final run: `Ran 25 tests in 0.426s`, `OK (skipped=1)`. The one skip is the deliberately
opt-in Linux integration test.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s adversarial -v
```

Observed final run: `Ran 4 tests in 0.082s`, `OK`.

## Linux namespace observations

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_host.py
```

Observed exactly:

```json
{"linux": true, "probe_exit_code": 0, "python": "3.11.5", "unshare_path": "/usr/bin/unshare", "user_namespace_probe": "AVAILABLE"}
```

The fuller namespace-only probe was bounded and returned exit status 0 with no program output:

```bash
/usr/bin/timeout --signal=KILL 10 /usr/bin/unshare --user --map-root-user --mount \
  --uts --ipc --pid --fork --kill-child=SIGKILL --net --mount-proc -- /bin/true
```

The first opt-in rootfs attempt used util-linux's path-valued
`--mount-proc=<temporary-root>/proc`. It failed (`Ran 1 test`, one failure) with:

```text
unshare: mount .../tmp3lq94jb3/root/proc failed: Invalid argument
```

A bounded diagnostic mounted procfs directly from inside the new user/mount/PID namespaces and
returned status 0:

```bash
mkdir -p .integration-probe/proc
/usr/bin/timeout --signal=KILL 10 /usr/bin/unshare --user --map-root-user --mount \
  --pid --fork --kill-child=SIGKILL -- /usr/bin/mount -t proc proc .integration-probe/proc
rmdir .integration-probe/proc .integration-probe
```

The reference was changed to perform that proc mount in the already-namespaced child. A subsequent
read-only-root attempt reached child setup but failed (`Ran 1 test`, one failure) with:

```text
minictr child: PermissionError: [Errno 1] Operation not permitted: '.../tmpxbaq_rpl/root'
```

Holding all other setup constant and setting `readonly_root: false` isolated this builder/filesystem
remount limitation. The final benign-workload smoke command was:

```bash
MINICTR_LINUX_INTEGRATION=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest sealed/reference_tests/test_linux_integration.py -v
```

Observed final run: `Ran 1 test in 0.260s`, `OK`. It copied `/bin/true`, `/lib64/libc.so.6`, and
`/lib64/ld-linux-x86-64.so.2` into a disposable temporary rootfs, entered the requested namespaces,
mounted procfs, chrooted, directly execed `/bin/true`, and removed the rootfs on exit. This does not
validate hostile workloads, read-only remounting, other kernels, or cleanup after abnormal host loss.

## Syntax, packaging, and hygiene

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c \
  'import ast,pathlib; files=sorted(pathlib.Path(".").rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in files]; print(f"AST_OK: {len(files)} Python files")'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/verify_pack.py
```

The final syntax scan printed `AST_OK: 35 Python files`. Packaging printed:

```text
OK: 23 required files; forbidden paths absent; regular entries only; metadata and credential scan clean
```

The verifier parsed both metadata files as strict JSON, compared the manifest to the authoritative
object, checked its provenance binding, rejected symlinks/special entries, checked every forbidden
path, and scanned regular files for private-key headers and common AWS/GitHub token shapes. No
upstream repository or linked tutorial was accessed. Bytecode created by an early integration child
was explicitly removed; the helper environment now disables bytecode writes, and the final scan found
no `__pycache__` directories or `.pyc` files.

## Exploratory timing (not a validation label)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  benchmarks/benchmark_reference.py --iterations 100
```

Observed exactly in the final-test run:

```text
iterations=100
plan_total_seconds=0.045508
sqlite_lifecycle_total_seconds=2.870975
```

This one uncontrolled microbenchmark does not earn or claim `BENCHMARKED`.

## Why status remains PARTIAL

Read-only remounting failed on the allocated workspace filesystem; the default Python is too old;
the integration rootfs was only an ephemeral host-derived `/bin/true` fixture; and cgroups, seccomp,
capability minimization, race-free path setup, a real init shim, bounded persistent logs, fuzzing,
transfer verification, and independent review are absent. No `BUILDS`, `TESTED`, `FUZZED`,
`BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is asserted here.
