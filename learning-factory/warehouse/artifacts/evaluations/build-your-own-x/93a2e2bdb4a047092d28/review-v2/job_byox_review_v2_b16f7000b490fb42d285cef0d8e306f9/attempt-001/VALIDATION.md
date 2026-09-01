# Independent validation log

## Scope and environment

All commands were run from `CANDIDATE/` unless noted. The submission was treated as immutable; Python bytecode writes were disabled, temporary state and benchmark output were directed to a reviewer scratch directory outside `CANDIDATE/`, and a final hash check matched the baseline.

```sh
REVIEW_PY=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
REVIEW_TMP=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_v2_b16f7000b490fb42d285cef0d8e306f9/attempt-001/.review-tmp.fFO80Z
python3 --version
python3 environment/check_python.py
env PYTHONDONTWRITEBYTECODE=1 "$REVIEW_PY" environment/check_python.py
```

Observed:

- inherited `python3`: CPython 3.6.8; candidate check exited 1 at `from __future__ import annotations`;
- explicit required toolchain: CPython 3.11.5; all Python sources compiled, exit 0;
- without `TMPDIR`, this sandbox's `/tmp`, `/var/tmp`, and candidate root were unusable by `tempfile`; test commands were repeated with `TMPDIR=$REVIEW_TMP`.

Every execution below also used `PYTHONDONTWRITEBYTECODE=1` and a 30-second `timeout`.

## Unit suites

```sh
env TMPDIR="$REVIEW_TMP" PYTHONPATH=sealed/reference "$REVIEW_PY" -m unittest discover -s public_tests -v
env TMPDIR="$REVIEW_TMP" PYTHONPATH=sealed/reference "$REVIEW_PY" -m unittest discover -s sealed/reference_tests -v
env TMPDIR="$REVIEW_TMP" PYTHONPATH=starter "$REVIEW_PY" -m unittest discover -s public_tests -v
```

| Target | Observed result |
|---|---|
| Reference / public | Exit 0; 4 tests passed |
| Reference / sealed recovery | Exit 0; 10 tests passed |
| Starter / public | Exit 1; 4 errors from intentional `NotImplementedError` stubs, with `close()` also masking original failures |

These are candidate-authored suites and are recorded as observations, not proof of TESTED status.

## Candidate-authored smoke tools

```sh
env TMPDIR="$REVIEW_TMP" KVSTORE_IMPL=reference "$REVIEW_PY" adversarial/fuzz/model_fuzz.py --operations 600
env TMPDIR="$REVIEW_TMP" KVSTORE_IMPL=reference "$REVIEW_PY" adversarial/stress/thread_stress.py --threads 6 --operations 80
env TMPDIR="$REVIEW_TMP" KVSTORE_IMPL=reference "$REVIEW_PY" adversarial/fault-injection/torn_tail.py
env TMPDIR="$REVIEW_TMP" KVSTORE_IMPL=buggy "$REVIEW_PY" debugging/lost-delete/test_bug.py
env TMPDIR="$REVIEW_TMP" KVSTORE_IMPL=reference "$REVIEW_PY" debugging/lost-delete/test_bug.py
```

Observed:

- model smoke: exit 0, seed 20260830, 600 operations;
- thread smoke: exit 0, 6 threads × 80 writes;
- torn-tail smoke: exit 0;
- lost-delete buggy target: exit 1 as expected; after reopen, `b'active'` was returned instead of `None`;
- lost-delete reference target: exit 0, 1 test passed.

The stress run was an additional reference-target check supported by the script, because the README's exact stress command targets the missing production implementation.

## Advertised commands that cannot run

```sh
"$REVIEW_PY" scripts/run_all.py
PYTHONPATH=production/implementation "$REVIEW_PY" -m unittest discover -s public_tests -v
PYTHONPATH=production/implementation "$REVIEW_PY" -m unittest discover -s sealed/reference_tests -v
KVSTORE_IMPL=production "$REVIEW_PY" adversarial/fuzz/model_fuzz.py --operations 600
KVSTORE_IMPL=production "$REVIEW_PY" adversarial/stress/thread_stress.py --threads 6 --operations 80
KVSTORE_IMPL=production "$REVIEW_PY" adversarial/fault-injection/torn_tail.py
KVSTORE_IMPL=production "$REVIEW_PY" debugging/lost-delete/test_bug.py
"$REVIEW_PY" benchmarks/benchmark.py --operations 500 --output "$REVIEW_TMP/review-smoke.json"
```

Observed:

- runner: exit 2, `scripts/run_all.py` does not exist;
- both production unit commands: exit 1, `ModuleNotFoundError: No module named 'kvstore'`;
- all four production script commands: exit 1 with the same missing-module cause;
- benchmark: exit 1 after the reference portion, `FileNotFoundError` for `production/implementation/kvstore.py`; no fresh comparison JSON was produced.

`production/PRODUCTIONIZATION.md`, also named by the README, is absent.

## Reviewer-authored behavioral probe

The reviewer executed an inline Python probe (via `-c`, with `PYTHONPATH=sealed/reference`) that:

1. set one key, verified deleting a missing key did not grow the log, applied a set/delete batch, and reopened;
2. appended an unterminated tail, reopened, verified committed state, and verified the tail was truncated;
3. stored four distinct values of `KVStore.MAX_VALUE_BYTES`, attempted compaction, then reopened.

Observed output, exit 0:

```text
independent_core=PASS missing_delete_no_append=true torn_tail_truncated=true
large_compaction=ValueError: batch is too large; reopened_keys=4
```

This independently supports the narrow core observations and demonstrates the undisclosed compaction capacity failure. It is not a crash or exhaustive test.

## Validation-tool false-positive probes

```sh
env TMPDIR="$REVIEW_TMP" KVSTORE_IMPL=reference "$REVIEW_PY" adversarial/fuzz/model_fuzz.py --operations 0
env TMPDIR="$REVIEW_TMP" KVSTORE_IMPL=reference "$REVIEW_PY" adversarial/stress/thread_stress.py --threads 0 --operations 80
env TMPDIR="$REVIEW_TMP" KVSTORE_IMPL=reference "$REVIEW_PY" -O adversarial/fault-injection/torn_tail.py
```

All three exited 0 and printed “passed.” The first two performed no model operations or thread work; the third ran with Python assertions removed.

## Structural, disclosure, and provenance checks

```sh
diff -u sealed/reference/kvstore.py debugging/lost-delete/buggy/kvstore.py
"$REVIEW_PY" -m json.tool PROVENANCE.json
"$REVIEW_PY" -m json.tool benchmarks/results/smoke.json
find . -type f \( -iname 'LICENSE*' -o -iname 'COPYING*' -o -iname 'NOTICE*' \) -print
```

Observed:

- the implementations have one source-line difference: delete replay versus `pass`;
- both JSON files parse;
- recomputation of each per-operation timing and the production/reference ratio matched the bundled benchmark JSON;
- no license/notice file was found;
- benchmark regeneration remained impossible, so numeric consistency does not authenticate provenance or measurements.

The manifest's cautious validation/deployment statuses were confirmed by text inspection. Its advertised instrumented variant and two alternatives do not match the submitted files.

## Immutability check

From the review workspace root:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Baseline aggregate: `31a95c6479fa37dc9f2874679eaaf862fd4eba60206ce0309d6b7931982a1be5`. Final aggregate: `31a95c6479fa37dc9f2874679eaaf862fd4eba60206ce0309d6b7931982a1be5`. File count remained 33; no symlinks were reported.

## Limitations

- The upstream checkout and network were unavailable, so commit, license, tutorial, copying, and validator-origin claims were not authenticated.
- No real power-loss, abrupt process termination, multi-process coordination, long campaign, coverage tool, or independent performance harness was available.
- Candidate-authored tests, fuzz/stress scripts, benchmark harness, and prose do not independently establish lifecycle labels.
