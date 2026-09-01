# Validation record

Review date: 2026-08-31. Commands were run from `CANDIDATE/` unless noted. Candidate writes and bytecode generation were disabled; every candidate file remained mode `0444` and no `__pycache__` or `.pyc` appeared.

The usable interpreter was:

```sh
PY=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11
```

Every bounded Python invocation used `PYTHONDONTWRITEBYTECODE=1 LC_ALL=C.UTF-8 timeout 25s` in addition to the command shown.

## Environment and source integrity

```sh
python3 --version
```

Observed: exit 0, `Python 3.6.8`. The documented unqualified commands cannot import these sources; `python3 environment/check_python.py` exited 1 at `from __future__ import annotations`.

```sh
$PY --version
$PY -c 'from pathlib import Path; files=sorted(Path(".").rglob("*.py")); [compile(path.read_bytes(),str(path),"exec") for path in files]; print(f"independently compiled {len(files)} Python files")'
$PY environment/check_python.py
```

Observed with the explicit interpreter: `Python 3.11.5`; the independent check compiled 16 files, and the candidate checker printed `all generated Python sources compile`. Both exited 0.

```sh
find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
find . -type d -name '__pycache__' -o -type f -name '*.pyc'
find . -type f ! -perm 0444 -print
```

Observed before review-output creation: aggregate candidate digest `18feaaec91fc83cdd96a733399b3ce1e621c6c5fa8bf16554c6cd3831af8bdf7`; the other two commands produced no paths. The digest was checked again after output creation with the same result.

## Candidate tests

The intentionally empty starter was used as a negative control:

```sh
PYTHONPATH=starter $PY -m unittest discover -s public_tests -v
```

Observed: exit 1; 5 tests ran and all 5 errored at the documented `NotImplementedError` stubs. This is expected exercise behavior, not reference validation.

The full public suite was attempted separately with each path:

```sh
PYTHONPATH=sealed/reference:sealed/shared $PY -m unittest discover -s public_tests -v
PYTHONPATH=sealed/alternatives/thread_per_connection:sealed/shared $PY -m unittest discover -s public_tests -v
PYTHONPATH=sealed/alternatives/event_loop:sealed/shared $PY -m unittest discover -s public_tests -v
```

Observed for each: exit 1; 3 parser/application tests passed and 2 network tests errored before setup at `socket.socket(...)` with `PermissionError: [Errno 1] Operation not permitted`.

The sealed contract suite was attempted with those same three implementation paths:

```sh
PYTHONPATH=sealed/reference:sealed/shared $PY -m unittest discover -s sealed/reference_tests -v
PYTHONPATH=sealed/alternatives/thread_per_connection:sealed/shared $PY -m unittest discover -s sealed/reference_tests -v
PYTHONPATH=sealed/alternatives/event_loop:sealed/shared $PY -m unittest discover -s sealed/reference_tests -v
```

Observed for each: exit 1; all 5 parser cases passed and all 7 network cases errored at forbidden socket creation. To isolate the executable pure checks:

```sh
PYTHONPATH=public_tests:sealed/reference:sealed/shared $PY -m unittest -v \
  test_http_service.PublicParserTests test_http_service.PublicApplicationTests
PYTHONPATH=sealed/reference_tests:sealed/reference:sealed/shared $PY -m unittest -v \
  test_contract.HiddenParserTests
```

Observed: exit 0, respectively 3/3 and 5/5 passing.

## Adversarial, debugging, and review exercises

```sh
PYTHONPATH=sealed/reference:sealed/shared $PY adversarial/parser/check.py \
  --seed 20260830 --iterations 2000
```

Observed: exit 0, `parser adversary passed seed=20260830 iterations=2000`.

```sh
PYTHONPATH=sealed/reference:sealed/shared $PY adversarial/fault-injection/check.py
PYTHONPATH=sealed/reference:sealed/shared $PY adversarial/slow-client/check.py
```

Observed: each exited 1 at initial socket creation with `PermissionError`; neither probe reached an assertion. Results are inconclusive.

```sh
PYTHONPATH=debugging/partial-body/buggy $PY debugging/partial-body/regression.py
PYTHONPATH=sealed/shared $PY debugging/partial-body/regression.py
```

Observed: the intended buggy negative control exited 1 with `parser emitted a request before Content-Length bytes arrived`; the corrected shared parser exited 0 and printed `fragmented body remained buffered until complete`.

```sh
PYTHONPATH=review_exercises/cache-layer/proposed:sealed/shared \
  $PY review_exercises/cache-layer/sealed/demonstrate.py
```

Observed: exit 0; it reproduced the documented cross-principal response disclosure.

## Independent edge probes

The counter-result boundary was checked directly:

```sh
PYTHONPATH=sealed/shared $PY -c 'import json; from http_core import CounterApp,Request; app=CounterApp(); put=app.handle(Request("PUT","/v1/counters/limit","HTTP/1.1",{"host":"x","content-type":"application/json","content-length":"23"},b"{\"value\":1000000000000}")); inc=app.handle(Request("POST","/v1/counters/limit/increment","HTTP/1.1",{"host":"x","content-type":"application/json","content-length":"11","idempotency-key":"bound-check"},b"{\"delta\":1}")); value=json.loads(inc.body)["value"]; print(f"put_status={put.status} increment_status={inc.status} resulting_value={value}"); assert abs(value)<=10**12, "stored counter escaped documented integer bound"'
```

Observed: exit 1 after printing `put_status=201 increment_status=200 resulting_value=1000000000001`; the boundary assertion failed.

The parser was fed a NUL target and an SOH Host value using `HTTPParser.feed` under `PYTHONPATH=sealed/shared`. Observed: exit 1 from the review assertion after both inputs were accepted:

```text
ACCEPTED target-NUL: target='/\x00' host='x'
ACCEPTED host-CTL: target='/' host='x\x01y'
```

Static inspection also found no absolute header/body read deadline in `serve_connection`; socket timeout is per `recv`. The event loop's inactivity timestamp is refreshed for every received fragment. The candidate slow-client probe sends one fragment and sleeps, so it does not test slow-drip progress.

## Benchmark and evidence artifacts

`MANIFEST.yaml`, `PROVENANCE.json`, and `benchmarks/results/smoke.json` were parsed with `json.loads`. An independent Python assertion checked project/job identity, three architecture keys, 40 sequential and 40 burst samples per architecture, medians, the harness's p95 formula, and `requests / burst_total` rates.

Observed: exit 0, `JSON parsed; identity fields and all archived sample counts/summaries are internally consistent`.

```sh
$PY benchmarks/benchmark.py --requests 5 --concurrency 1 \
  --output ../review-benchmark-observed.json
```

Observed: exit 1 at the first server's socket creation with `PermissionError`; no output file was created. Thus the archived numbers were integrity-checked but not independently reproduced.

## Documentation, disclosure, and licensing checks

```sh
$PY scripts/run_all.py
for item in scripts/run_all.py production production/PRODUCTIONIZATION.md; do
  test -e "$item" && printf 'PRESENT %s\n' "$item" || printf 'MISSING %s\n' "$item"
done
find . -type f \( -iname 'LICENSE*' -o -iname 'COPYING*' -o -iname 'NOTICE*' \) -print
```

Observed: the first command exited 2 with file-not-found; all three referenced paths were `MISSING`; the license-file search returned no paths. The solution/reference material is organized below sealed directories and the README candidly describes a manual human reveal boundary, but there is no generated student-view artifact or automated leak check.

`PROVENANCE.json` records the job/project identity, source commit, upstream URL, CC0-1.0 metadata, generated/source-derived categories, and an outbound-content boundary. The external source tree and URL were unavailable under workspace restrictions, so those statements could not be independently verified.

## Limitations and validation-label disposition

- AF_INET socket creation is denied, so network behavior, lifecycle, overload, concurrency, fault isolation over the wire, slow clients, and fresh benchmark measurements are inconclusive.
- `git` and `rg` were not installed; `find`, `sha256sum`, and `grep` supplied deterministic local fallbacks.
- Builder-authored tests/probes and the archived benchmark are useful subjects of review but do not alone prove `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.
- The manifest appropriately remains `GENERATED_CANDIDATE`, `NOT_PRODUCTION_READY`, `productionized: false`, and describes validation targets rather than completed labels. This review did not modify it.
