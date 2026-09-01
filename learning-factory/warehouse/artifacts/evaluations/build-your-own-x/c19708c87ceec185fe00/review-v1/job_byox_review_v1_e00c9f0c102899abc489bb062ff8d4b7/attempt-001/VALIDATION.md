# Validation record

## Scope and environment

Commands were run from `CANDIDATE/` unless noted. Candidate execution used bounded timeouts,
`PYTHONDONTWRITEBYTECODE=1`, and `LC_ALL=C.UTF-8`; benchmark output was directed to `/tmp`. No file
inside CANDIDATE was edited. The aggregate file hash was identical before and after testing:

```text
b29066b50f6bb9f50c50a443499dcf8db0c328b7eeb7e5ecf0e35be1c06366d9
```

Toolchain observations:

```sh
python3 --version
command -v python3
command -v timeout
```

```text
Python 3.11.5
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
/bin/timeout
```

The standard-library `selectors`, `socket`, and `threading` modules imported. Actual AF_INET socket
creation was denied by the review sandbox with `PermissionError: [Errno 1] Operation not permitted`.

## Static and metadata checks

```sh
timeout 30s env PYTHONDONTWRITEBYTECODE=1 LC_ALL=C.UTF-8 \
  python3 environment/check_python.py
```

Exit 0: `all generated Python sources compile`.

```sh
python3 -m json.tool MANIFEST.yaml >/dev/null
python3 -m json.tool PROVENANCE.json >/dev/null
python3 -m json.tool benchmarks/results/smoke.json >/dev/null
```

All three exited 0. A separate recomputation confirmed 40 sequential and 40 burst samples for each
of the three architectures; stored medians, p95 values, and request-per-second calculations match
the raw values. This checks internal arithmetic only, not who executed the benchmark.

```sh
find CANDIDATE -type f \( -iname 'LICENSE*' -o -iname 'COPYING*' \
  -o -iname 'NOTICE*' \) -print
find CANDIDATE -type l -print
```

Both produced no paths.

The local repository recorded in `PROVENANCE.json` was inspected read-only:

```sh
git rev-parse HEAD
git cat-file -t aa17439b62f384511a5561ce308e9598b94d8989
git show aa17439b62f384511a5561ce308e9598b94d8989:README.md | \
  nl -ba | sed -n '418,426p;501,505p'
```

The HEAD and recorded object are commit `aa17439b62f384511a5561ce308e9598b94d8989` (2026-07-14).
The README contains the recorded A Simple Web Server link at line 425 and the catalog repository's
CC0 waiver at lines 501-505. This does not determine the linked tutorial's license or license the
new pack.

## Candidate-provided tests and exercises

Common prefix below:

```sh
timeout 30s env PYTHONDONTWRITEBYTECODE=1 LC_ALL=C.UTF-8
```

The learner command was run with `PYTHONPATH=starter`:

```sh
python3 -m unittest discover -s public_tests -v
```

Exit 1: five of five tests errored at the starter's intentional `NotImplementedError` stubs. This
matches the documented expectation and is not treated as a reference failure.

The public suite was then run with each of these import paths:

```text
PYTHONPATH=sealed/reference:sealed/shared
PYTHONPATH=sealed/alternatives/thread_per_connection:sealed/shared
PYTHONPATH=sealed/alternatives/event_loop:sealed/shared
```

For every architecture, three parser/application tests passed and two network tests errored only
when `socket.socket(AF_INET, SOCK_STREAM)` returned EPERM. Exit 1 is therefore environmental and
does not establish either pass or fail for the network behavior.

The same three paths were used with:

```sh
python3 -m unittest discover -s sealed/reference_tests -v
```

For each architecture, five parser tests passed and seven network tests errored at socket creation.
The non-network groups were also isolated to avoid conflating them with the environment failure:

```sh
PYTHONPATH=sealed/reference:sealed/shared:public_tests \
  python3 -m unittest -v test_http_service.PublicParserTests \
  test_http_service.PublicApplicationTests
PYTHONPATH=sealed/reference:sealed/shared:sealed/reference_tests \
  python3 -m unittest -v test_contract.HiddenParserTests
```

Exit 0: 3/3 public parser/application tests and 5/5 sealed parser tests passed. Repeating the pure
tests through the alternatives also passed, but all variants import the same `sealed/shared`
parser/application code, so these are not three independent core implementations.

```sh
PYTHONPATH=sealed/reference:sealed/shared \
  python3 adversarial/parser/check.py --seed 20260830 --iterations 120
```

Exit 0: `parser adversary passed seed=20260830 iterations=120`. The same check exited 0 through
both alternative paths. Its scope is one fixed valid wire message under randomized chunk widths and
six fixed invalid messages.

```sh
PYTHONPATH=debugging/partial-body/buggy \
  python3 debugging/partial-body/regression.py
PYTHONPATH=sealed/shared python3 debugging/partial-body/regression.py
PYTHONPATH=review_exercises/cache-layer/proposed:sealed/shared \
  python3 review_exercises/cache-layer/sealed/demonstrate.py
```

Observed results:

- Buggy regression: exit 1 at the intended early-emission assertion.
- Corrected shared parser: exit 0, `fragmented body remained buffered until complete`.
- Cache demonstration: exit 0 and reproduced cross-principal response disclosure.

The advertised aggregate command was also run:

```sh
python3 scripts/run_all.py
```

Exit 2: `scripts/run_all.py` does not exist. `production/PRODUCTIONIZATION.md` does not exist either.

## Independent contract probes

### Decimal Content-Length conversion

```sh
PYTHONPATH=sealed/shared python3 - <<'PY'
from http_core import HTTPParser, ProtocolError
payload = (b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: "
           + b"9" * 5000 + b"\r\n\r\n")
try:
    HTTPParser().feed(payload)
except ProtocolError as error:
    print("structured", error.status)
except Exception as error:
    raise AssertionError(f"expected ProtocolError, got {type(error).__name__}: {error}")
PY
```

Exit 1. Observed `ValueError: Exceeds the limit (4300 digits) for integer string conversion`, then
the probe assertion. The input header remains below the configured 8,192-byte header cap.

### Chunk-invariant parsing

```sh
PYTHONPATH=sealed/shared python3 - <<'PY'
from http_core import HTTPParser, ProtocolError
valid = b"GET /healthz HTTP/1.1\r\nHost: x\r\n\r\n"
invalid = b"GET / HTTP/1.1\r\n\r\n"
def run(chunks):
    parser, emitted, errors = HTTPParser(), [], []
    for chunk in chunks:
        try:
            emitted.extend(parser.feed(chunk))
        except ProtocolError as error:
            errors.append(error.status)
    return [request.target for request in emitted], errors
combined, split = run([valid + invalid]), run([valid, invalid])
print("combined", combined)
print("split", split)
assert combined == split
PY
```

Exit 1:

```text
combined ([], [400])
split (['/healthz'], [400])
```

### Bare LF in request target

```sh
PYTHONPATH=sealed/shared python3 - <<'PY'
from http_core import HTTPParser, ProtocolError
payload = b"GET /ok\nInjected:yes HTTP/1.1\r\nHost: x\r\n\r\n"
try:
    requests = HTTPParser().feed(payload)
except ProtocolError as error:
    print("rejected", error.status)
else:
    raise AssertionError(f"bare LF accepted in target: {requests[0].target!r}")
PY
```

Exit 1: `bare LF accepted in target: '/ok\nInjected:yes'`.

### JSON and accumulated integer bounds

A 5,000-digit JSON integer was sent directly through `dispatch(CounterApp(), request)`. The probe
expected a stable 4xx and exited 1 after observing:

```text
status 500 body {"error":"internal server error"}
```

A second probe put `1000000000000`, then incremented by one. It exited 1 after observing:

```text
status 200 value 1000000000001
```

### Network-dependent probes and benchmark

```sh
PYTHONPATH=sealed/reference:sealed/shared python3 adversarial/fault-injection/check.py
PYTHONPATH=sealed/reference:sealed/shared python3 adversarial/slow-client/check.py
python3 benchmarks/benchmark.py --requests 5 --concurrency 2 \
  --output /tmp/job_byox_review_benchmark.json
```

Each exited 1 at the first `socket.socket()` call with EPERM. No behavioral or performance
conclusion is drawn from those results, and the existing candidate-supplied smoke JSON was not
treated as controller evidence.

## Validation-label assessment

| Label | Independent result |
|---|---|
| `BUILDS` | Narrow syntax/import viability supported; this is not full service validation. |
| `TESTED` | Not established broadly; pure subsets pass, independent probes fail, network surface is inconclusive. |
| `FUZZED` | Not established; only a small deterministic fragmentation campaign passed. |
| `BENCHMARKED` | Candidate JSON is internally consistent, but fresh execution was blocked and no attestation binds the stored run to this artifact. |
| `REVIEWED` | This independent review completed and found acceptance blockers; builder-authored review prose is not prior proof. |
| `TRANSFER_VERIFIED` | Not tested; no mechanical learner-only view was supplied. |
| `PRODUCTIONIZED` | Correctly unsupported and explicitly false. |
| `PARTIAL` | Supported. |

## Limitations

- The sandbox's socket policy prevented all architecture-specific end-to-end, overload, shutdown,
  slow-client, fault-injection, and fresh benchmark checks.
- External network access was not used, so live tutorial content/license and the no-copy claim were
  not independently verified.
- No controller validation log was available in the review workspace.
- CANDIDATE alone does not reveal whether its missing documented files were omitted by the builder
  or by review staging.
- No generated student view was available to test sealed-material exclusion.
