# Independent review

Verdict: **REVISE**. The generation-2 runtime repair itself held up under fresh
host/ARM execution and an independent distinguishing probe. One harness-safety
defect should be fixed before advisory acceptance; the remaining findings are
evidence and learner-clarity improvements. This review does not promote any
manifest label.

## Prioritized findings

### P1 — The ARM runner's output limit is enforced only after unbounded capture

`sealed/reference_tests/run_runtime_qemu.py:79` uses
`process.communicate(timeout=...)`, which accumulates all merged QEMU output in
memory. Only after QEMU exits does line 88 compare `len(output)` with
`MAX_OUTPUT` (65,536 bytes). The timeout bounds duration, not memory. A broken
image that continuously writes the UART can therefore exhaust worker memory
before the advertised capture limit rejects it.

A reviewer-controlled 8 MiB producer was fully consumed before the runner
reported `captured output exceeds 65536 bytes`; the measured runner command
reached 28,088 KiB maximum resident memory. Replace `communicate()` with
incremental reads that retain at most the limit, terminate the process group as
soon as the ceiling is crossed, and boundedly drain/reap it. The selector-based
pattern already used in `adversarial/run_vectors.py` is a suitable model. Add a
test proving both the retained-byte ceiling and process-group cleanup under a
continuing output flood.

### P2 — The submitted stale-frame regression does not distinguish extra rotation

`sealed/reference_tests/runtime_reentrancy.c:36-40` creates only one runnable
replacement before selecting it. If stale-yield code incorrectly rotated again,
round-robin selection would choose that same singleton, so the existing marker
sequence would still pass. This leaves the explicit requirement to dispatch an
already-selected identity without rotating it away without a durable,
discriminating regression.

The current implementation appears correct: a separate ARM probe created two
ready replacements, preselected the first, then yielded from the stale physical
frame. QEMU printed `SELECTED-FIRST`, then `OTHER-SECOND`, and passed. Preserve
that shape in the sealed suite so future changes cannot regress it.

### P3 — Learner-facing provenance and polling guidance have two broken edges

- `LICENSE_BOUNDARY.md:3` directs learners to `PROVENANCE.json`, but neither
  disclosure policy includes that file. Include the safe provenance record in
  both stages, or explain that it is evaluator-held and put the learner-relevant
  source/license identifiers directly in the boundary document.
- `starter/kernel/uart.c:3-4` asks for "bounded polling," while the reference
  polls indefinitely and `sealed/REVIEW.md` explicitly accepts a permanently
  full UART as a hang limitation. The void API also provides no timeout result.
  Align the starter comment with the actual contract, or define and test real
  bounded behavior.

## What held up

- Manifest labels are conservative and validation prose explicitly separates
  builder evidence from independent promotion.
- Fresh sanitizer-backed suites, deterministic vector cases, cross-builds, ELF
  checks, nominal QEMU boot, and the stale-yield/stale-return ARM probe all
  reproduced their recorded outcomes.
- The rebuilt reference and starter artifacts exactly matched every recorded
  hash and size.
- Actual initial and post-attempt views matched their deterministic inventory
  hashes. Independent inspection found no sealed/reference/answer material;
  the post-attempt delta was exactly the intended exercises.
- Requirements, concepts, starter stubs, public feedback, sealed rationale, and
  production limitations are meaningfully separated. The license boundary is
  explicit about CC0 metadata, the unasserted linked-resource license, and the
  all-rights-reserved generated content.

## Review limitations

The supplied workspace contains neither `PRIOR_BUILD` nor the cited controller
audit, so the historical comparison could not be repeated. No immutable
upstream snapshot or network was available to test the non-copying assertion.
Target execution was QEMU only. No physical-board, fuzz, benchmark, formal,
broad-security, or production claim was evaluated.
