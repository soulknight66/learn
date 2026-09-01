# Independent validation record

Review date: 2026-08-31  
Working directory: `CANDIDATE/` unless stated otherwise  
Host: CPython 3.11.5 on Linux 4.18.0 x86_64

`CANDIDATE/` was treated as immutable. Python checks used `PYTHONDONTWRITEBYTECODE=1`; test data went to temporary directories, and the benchmark output was redirected to `/tmp`.

## Inventory and integrity

```sh
find CANDIDATE -type f -printf '%P\n' | sort
find CANDIDATE -type l -print
find CANDIDATE -type f -exec sha256sum {} + | sort -k2 | sha256sum
```

Observed: 33 regular files, no symlinks, and aggregate digest `31a95c6479fa37dc9f2874679eaaf862fd4eba60206ce0309d6b7931982a1be5`. The same digest was observed before and after all candidate checks. No `__pycache__` directory was created.

Direct path checks found all of the following absent:

```text
scripts/run_all.py
production/implementation/kvstore.py
production/PRODUCTIONIZATION.md
```

## Available reference checks

```sh
PYTHONDONTWRITEBYTECODE=1 python3 environment/check_python.py
```

Exit 0: `all Python sources compile`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m unittest discover -s public_tests -v
```

Exit 0: 4 tests ran and passed.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m unittest discover -s sealed/reference_tests -v
```

Exit 0: 10 tests ran and passed, including the POSIX directory-fsync test; no tests were skipped.

```sh
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=reference \
  python3 adversarial/fuzz/model_fuzz.py --operations 600
```

Exit 0: `model fuzz passed: implementation=reference seed=20260830 operations=600`.

```sh
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=reference \
  python3 adversarial/stress/thread_stress.py --threads 6 --operations 80
```

Exit 0: `thread stress passed: implementation=reference threads=6 operations=80`.

```sh
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=reference \
  python3 adversarial/fault-injection/torn_tail.py
```

Exit 0: `torn-tail recovery and post-recovery compaction passed: implementation=reference`.

```sh
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=buggy \
  python3 debugging/lost-delete/test_bug.py
```

Exit 1, intentionally: one test failed because reopen returned `b'active'` instead of `None`. This reproduces the challenge's documented lost-delete symptom.

```sh
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=reference \
  python3 debugging/lost-delete/test_bug.py
```

Exit 0: one test ran and passed.

These results independently validate only the submitted sealed reference under this bounded workload. They do not validate the absent production/instrumented variant.

## Documented commands that could not run

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_all.py
```

Exit 2: Python reported `No such file or directory` for `CANDIDATE/scripts/run_all.py`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=production/implementation \
  python3 -m unittest discover -s public_tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=production/implementation \
  python3 -m unittest discover -s sealed/reference_tests -v
```

Each exited 1. Test discovery produced an import error: `ModuleNotFoundError: No module named 'kvstore'`.

```sh
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=production \
  python3 adversarial/fuzz/model_fuzz.py --operations 600
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=production \
  python3 adversarial/stress/thread_stress.py --threads 6 --operations 80
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=production \
  python3 adversarial/fault-injection/torn_tail.py
```

Each exited 1 with `ModuleNotFoundError: No module named 'kvstore'` because the mapped production directory is absent.

To avoid overwriting the submitted result, the documented benchmark was redirected to `/tmp`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 benchmarks/benchmark.py \
  --operations 500 \
  --output /tmp/kvstore-review-smoke-attempt-002.json
```

Exit 1: `FileNotFoundError` for `CANDIDATE/production/implementation/kvstore.py`. No fresh benchmark JSON was produced. The submitted `benchmarks/results/smoke.json` was only inspected; it was not altered.

## Independent edge checks

The compaction boundary probe used three keys whose values were each exactly `KVStore.MAX_VALUE_BYTES`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -c \
  'import tempfile; from pathlib import Path; from kvstore import KVStore; t=tempfile.TemporaryDirectory(); p=Path(t.name)/"store.log"; s=KVStore(p,sync=False); v=b"x"*s.MAX_VALUE_BYTES; [s.set(str(i).encode(),v) for i in range(3)]; print(f"pre_compact_bytes={p.stat().st_size}"); s.compact(); s.close(); t.cleanup()'
```

Exit 1. It printed `pre_compact_bytes=4194627`, then raised `ValueError: batch is too large` from `_encode()` during `compact()`.

The incomplete-record boundary probe created a tail one byte larger than `MAX_RECORD_BYTES`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -c \
  'import tempfile; from pathlib import Path; from kvstore import KVStore; t=tempfile.TemporaryDirectory(); p=Path(t.name)/"store.log"; p.write_bytes(b"x"*(KVStore.MAX_RECORD_BYTES+1)); print(f"tail_before={p.stat().st_size}"); s=KVStore(p,sync=False); s.close(); print(f"tail_after={p.stat().st_size}"); t.cleanup()'
```

Exit 0: `tail_before=4194305` and `tail_after=0`. The oversized unterminated record was not rejected.

The fuzzer argument check was:

```sh
PYTHONDONTWRITEBYTECODE=1 KVSTORE_IMPL=reference \
  python3 adversarial/fuzz/model_fuzz.py --operations -1
```

Exit 0: it printed `model fuzz passed: implementation=reference seed=20260830 operations=-1` despite running no operation.

## Provenance checks

Against the local read-only source repository named in `PROVENANCE.json`:

```sh
git -C /projects/se/pj34000401_refsys/users/yuali01/learn/build-your-own-x \
  rev-parse HEAD
git -C /projects/se/pj34000401_refsys/users/yuali01/learn/build-your-own-x \
  cat-file -t aa17439b62f384511a5561ce308e9598b94d8989
git -C /projects/se/pj34000401_refsys/users/yuali01/learn/build-your-own-x \
  show aa17439b62f384511a5561ce308e9598b94d8989:README.md
```

Observed: `HEAD` exactly matched the declared commit; the object type was `commit`; the pinned README contained the cited Python DBDB URL and an Origins & License section with a CC0 waiver. The pinned repository had no standalone `LICENSE` file. No local snapshot or independently established license for the externally linked tutorial was supplied.

## Limitations

- The production/instrumented source is unavailable, so all claims about that target are inconclusive.
- The stored benchmark cannot be replayed and lacks enough run identity to authenticate it independently.
- The torn-tail script appends bytes after a clean close; it is not a real process-crash, power-loss, or filesystem fault campaign.
- The external tutorial was not fetched. Its license and non-derivation relationship to generated material were not independently checked.
- Fuzzing and thread stress were one deterministic bounded run each, not exhaustive verification.
- Progressive disclosure was assessed from the submitted archive. No separately generated student view was available to test.
