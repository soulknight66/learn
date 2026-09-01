# Independent review

Verdict: **REVISE**. The pack has a strong teaching shape and is candid about being partial and
not production-ready, but the reference has contract-level parsing defects, the reviewable tree
cannot run its advertised aggregate validation, and several evidence and licensing boundaries are
not strong enough for promotion.

## Prioritized findings

### Critical — a legal-size header can terminate serving threads

`CANDIDATE/sealed/shared/http_core.py:156-161` converts any decimal `Content-Length` with
`int()` before comparing it with the body limit. On the supplied CPython 3.11, a 5,000-digit value
fits under the default 8,192-byte header limit but raises the interpreter's integer-conversion
`ValueError`. Connection handling catches only `ProtocolError`
(`CANDIDATE/sealed/shared/http_core.py:367-373`), as does the selector loop
(`CANDIDATE/sealed/alternatives/event_loop/http_service.py:119-125`). The independent probe
observed the uncaught `ValueError`. It can kill a fixed-pool worker; on the selector architecture it
can kill the sole event-loop thread. This violates the bounded-input and stable-4xx contract in
`CANDIDATE/REQUIREMENTS.md:5-10,30-31`.

### Major — completed requests are lost depending on TCP chunking

`HTTPParser.feed()` accumulates completed requests locally, but continues parsing buffered
pipelined bytes before returning them (`CANDIDATE/sealed/shared/http_core.py:103-166`). If a later
request in the same `feed()` call is malformed, the exception discards the already completed local
results. The same bytes produced these observations:

- one feed: `combined ([], [400])`
- two feeds: `split (['/healthz'], [400])`

That makes application behavior depend on arbitrary transport segmentation, directly opposing
`CANDIDATE/REQUIREMENTS.md:5-6`. A regression should cover a valid frame followed by a malformed
frame in both combined and split delivery.

### Major — bare newline/control bytes are accepted in the request target

The target check only requires a leading slash, excludes `#`, and decodes ASCII
(`CANDIDATE/sealed/shared/http_core.py:128-134`). The bare-newline check at lines 109-115 does not
catch a lone LF when a later valid `CRLFCRLF` terminator exists. The independent probe accepted
`'/ok\nInjected:yes'` as a target. This is neither the promised origin-form validation nor the
promised rejection of bare-newline framing (`CANDIDATE/REQUIREMENTS.md:5-8`).

### Major — integer validation does not produce the promised bounded, stable behavior

`CounterApp._payload()` catches UTF-8 and JSON syntax errors, but not the `ValueError` produced by
CPython's integer digit limit (`CANDIDATE/sealed/shared/http_core.py:204-216`). `dispatch()` then
maps that client input to 500. A 5,000-digit JSON integer independently returned
`500 {"error":"internal server error"}` rather than a stable 4xx. Separately, payloads are capped
at `10**12`, but increment results at lines 268-279 are not range-checked: putting `10**12` and
incrementing by one stored `1000000000001`. Both conflict with the bounded-integer requirement at
`CANDIDATE/REQUIREMENTS.md:30`.

### Major — the reviewable submission is not self-contained

`CANDIDATE/README.md:40-46` says `python3 scripts/run_all.py` runs every bounded factory check, but
the command exits 2 because `scripts/run_all.py` is absent. The referenced
`production/PRODUCTIONIZATION.md` and navigation target `production/` are also absent
(`CANDIDATE/README.md:46,57`). `sealed/REVIEW.md` does retain a useful production-gap discussion,
but the documented workflow and link are broken. Whether this happened during builder packaging or
review staging cannot be determined from CANDIDATE; either way, a learner or reviewer cannot follow
the submitted instructions.

### Major — validation targets are broader than the available evidence

The restraint in `MANIFEST.yaml` is good: the labels are `validation_targets`, the status remains
`GENERATED_CANDIDATE`, and production is false. They must not be promoted on current evidence:

- The parser “fuzz” script varies only fragmentation widths for one constant valid message and
  checks six fixed invalid messages (`CANDIDATE/adversarial/parser/check.py:9-43`). It missed the
  framing defects above and is only a deterministic smoke probe.
- `sealed/REVIEW.md` is useful builder-authored prose, not independent `REVIEWED` evidence.
- `benchmarks/results/smoke.json` is arithmetically consistent, but lacks an execution time, source
  digest/revision, controller run ID, and explicit validation label. `PROVENANCE.json:27-29` names
  it as measured without binding it to an attested run.
- The three architectures share the same parser and application core. Repeated core-test passes are
  not independent implementations, and the architecture-specific network surface was unavailable
  in this sandbox.

Independent execution supports syntax/import viability and a narrow subset of parser/application
behavior. It does not establish broad `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` status.

### Major — generated-content licensing is unspecified

`PROVENANCE.json:2-15` correctly scopes CC0 to the Build Your Own X catalog source; the recorded
commit and its CC0 statement were verified locally. It also correctly says the outbound tutorial
remains under its own terms. However, the pack identifies nearly all substantive material as newly
agent-generated (`PROVENANCE.json:16-22`) and includes no `LICENSE`, `COPYING`, `NOTICE`, or SPDX
declarations for that material. A downstream learner or distributor therefore cannot determine
reuse terms. The catalog's CC0 statement must not silently be treated as licensing the linked
tutorial or the newly generated pack.

### Moderate — progressive disclosure is documented but not demonstrated

The starter, public tests, reference, withheld checks, diagnoses, and expected review are clearly
organized. `CANDIDATE/README.md:25-27` is also honest that `sealed/` is only a human reveal boundary
and instructs operators to construct a separate student view. No learner-view manifest, mechanical
allowlist check, or transfer evidence is included in the reviewable tree, so exclusion of sealed
answers cannot be credited as `TRANSFER_VERIFIED`. The absolute internal source path in
`PROVENANCE.json:11` is also non-portable and exposes an unnecessary username/path to any learner
who receives this file.

### Moderate — some grading behavior is under-specified

The learner contract says names and integers are bounded without publishing the chosen limits, and
it says `If-Match` prevents stale writes without specifying the error status
(`CANDIDATE/REQUIREMENTS.md:28-30`). The sealed test requires 409
(`CANDIDATE/sealed/reference_tests/test_contract.py:142-160`), while a reasonable HTTP-oriented
implementation could choose 412. Deterministic grading criteria should state externally observable
limits and statuses rather than reveal them only through the reference behavior.

## What is useful and honest

- `REQUIREMENTS.md`, `CONCEPTS.md`, and `DESIGN_QUESTIONS.md` form a coherent progression from byte
  streams through concurrency, idempotency, shutdown, and operations.
- The worker-pool, bounded-thread, and selector variants keep a shared API and explain meaningful
  tradeoffs without claiming one universal winner.
- The intentionally incomplete starter is clearly labeled; its public test failure is expected.
- The partial-body debugging regression and cache-review disclosure demonstration both reproduce
  their intended lessons.
- Raw benchmark samples and an interpretation boundary are present, and the text avoids turning one
  smoke run into a capacity claim.
- The catalog commit, relationship, and CC0 statement are traceable; no mirrored tutorial content,
  credential-like material, or symlinks were found in the submitted tree.
- `PARTIAL`, `NOT_PRODUCTION_READY`, and `productionized: false` are appropriate and honest.

## Acceptance conditions

Before promotion, resolve the parser and integer-bound failures with deterministic regressions;
make the submitted validation and production-documentation paths self-contained; specify learner-
visible status/limit semantics; declare generated-content licensing; create and verify a mechanical
learner-only view; and rerun the full architecture, adversarial, and benchmark matrix under a
controller-owned harness that can use loopback sockets and records artifact-bound evidence.
