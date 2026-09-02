# Independent review

Verdict: **REVISE**.

The reference implementation and isolation mechanism are substantially sound, and the builder's major
test-count, digest, boundary, and status claims reproduced. Two material issues and one lower-priority
progressive-disclosure gap should be resolved before an advisory pass.

## Prioritized findings

### P1 — Resolve the `empty?` operand contract and test it

`REQUIREMENTS.md:79` defines `empty?` in terms of an empty list or `nil`, and lines 86–87 state that a
wrong operand type raises `EvalError`. The reference instead installs a total predicate at
`sealed/reference/pebble/interpreter.py:275`: every non-list, non-`nil` value returns `false`.

Independent results were:

```text
(empty? 1) -> value:false
(empty? false) -> value:false
(empty? "") -> value:false
(empty? +) -> value:false
```

This is at least a normative ambiguity and, under the blanket wrong-type rule, a reference-contract
violation. Learners can reasonably implement different behavior, while neither public nor sealed tests
settle it. Choose one contract explicitly: either accept only lists/`nil` and raise `EvalError` otherwise,
or state that `empty?` accepts every Pebble value and returns `false` for all other values. Make the
reference and deterministic public/sealed regression tests match that choice.

### P2 — Make learner-visible provenance and license guidance self-contained

`README.md:8-9` tells learners to inspect `PROVENANCE.json` and `LICENSE_BOUNDARY.md`. The export allowlist
at `sealed/production/learner_view.py:12-22` omits both. An actual export confirmed that the README still
contains both pointers while neither target exists.

The omission does prevent sealed material from leaking, which is good, but it also prevents the learner
from checking the evidence offered for the origin and license-boundary claims. Include learner-safe copies
of those two documents in the allowlist, or replace the pointers with a complete learner-visible summary.
Add a test that every learner-facing provenance/license pointer resolves without adding any sealed path.

### P3 — Define whether supplemental prompts have a learner reveal stage

The only exported view is the core scaffold. Learner-safe material under `adversarial/`, `benchmarks/`,
and the prompt/code portions of `debugging/` and `review_exercises/` is absent, and no later-stage export is
defined. This is not a secrecy failure, but it leaves much of the pack's claimed learner value dependent on
an unspecified harness action. Either document those roots as instructor-only or add deterministic staged
allowlists that copy prompt files while continuing to exclude each local `sealed/` directory.

## Passing observations

- Python 3.11.5 runtime preflight passed. Java 21.0.5 was available but irrelevant to this Python pack.
- The public reference suite passed 23/23; the sealed suite passed 63/63.
- Independent probes confirmed lexical scope, combined tail positions at 5,500 calls, reader nesting and
  integer limits, stable host limits, controlled error classes, and byte-faithful learner export.
- All 33 Python files parsed. The AST scan found no calls to Python `eval`, `exec`, or `compile`, and no
  `shell=True` subprocess call.
- The export had exactly nine roots and 20 files, used modes 0755/0644, and contained no sealed,
  reference, hidden-test, solution, or answer path.
- Manifest and provenance canonical digests matched the builder's recorded values. The manifest honestly
  remains `GENERATED` + `PARTIAL`, with `productionized: false` and independent validation required.
- The starter's public-suite failure was reproduced and is clearly represented as intentional incompleteness.
- No credential-shaped content or unusual filesystem entry was found. The source tree fingerprint was
  identical before and after review.

## Review limitations

No network or upstream repository was accessed, so source, commit, and license assertions remain
unconfirmed external provenance. No fuzz, benchmark, security, performance, transfer, or production claim
was evaluated. The exporter was tested, but the orchestrator's eventual access-control and transfer path
was not observable here.
