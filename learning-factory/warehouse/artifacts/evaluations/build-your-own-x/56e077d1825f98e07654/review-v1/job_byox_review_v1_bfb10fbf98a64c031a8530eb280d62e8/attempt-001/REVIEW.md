# Independent review

## Verdict

**REVISE.** The package is candid about its `GENERATED`/`PARTIAL` status, and its ordinary host
builds and tests reproduce. One independently reproduced scheduler identity defect prevents the
sealed implementation from serving as a reliable contract oracle. The candidate was not modified.

## Prioritized findings

### P1 — A callback result can be applied to a different task

`REQUIREMENTS.md:48-50` says a callback result is applied only if the callback left *the task*
running. The candidate also calls the callback interface reentrant in `sealed/REVIEW.md:20`.

A callback for PID 1 can legally exit, reap itself, spawn PID 2 into the now-free slot, and invoke a
nested tick. With quantum 2, PID 2 remains running after that nested tick. When PID 1's callback then
returns `MK_STEP_EXIT`, `sealed/reference/src/kernel.c:265-267` checks identity only for the step
counter; `:268-285` applies the result based solely on the slot's current `RUNNING` state. The
independent reproducer observed:

```text
pid=2 state=4 exit=0 steps=1 calls=1 now=2
```

Thus PID 2 was incorrectly made `MK_TASK_ZOMBIE` by PID 1's result. Preserve the captured PID when
deciding whether to apply the result, or explicitly forbid and enforce rejection of nested
`mk_tick`/`mk_run` calls. Add this sequence to the sealed suite.

### P2 — Generated-material reuse terms are not explicit

`LICENSE_BOUNDARY.md` correctly separates the CC0 catalog record from the linked repository's
`NOASSERTION` license and does not infer permission from the URL. However, “independently generated
for personal educational use” is a provenance statement, not a license grant. Add an explicit
license/SPDX identifier for the generated pack, or state clearly that no redistribution license is
granted. The upstream independence claim could not be checked from this isolated workspace.

### P3 — Required query sentinels are absent from the public header

`REQUIREMENTS.md:9-10` says query sentinel values are documented in the header, but
`starter/include/tinyarm.h:97-126` contains declarations without such documentation. Learners must
infer the null/error behavior of `mk_has_live_tasks`, `mk_current_pid`, `mk_task`,
`mk_vm_free_frames`, and `mk_fs_free_blocks`. Document those return conventions in the ABI header.

## Progressive disclosure and learner usefulness

The conceptual guide, staged progression, design questions, intentionally incomplete starter, and
narrow public-test disclosure are useful and avoid presenting the reference algorithm as learner
material. The public suite is small for the size of the contract, but its omissions are stated
honestly.

The evaluator bundle contains 20 readable files under `sealed/`, including the complete solution,
hidden tests, and answers. Directory naming and prose are not evidence that a student export excludes
them. No learner-view artifact or export/allowlist validation was supplied, so transfer isolation is
inconclusive. This is appropriately not labeled `TRANSFER_VERIFIED`; a harness-controlled learner
view must exclude `sealed/` before delivery.

## Positive evidence

- Both JSON-formatted metadata files parse and agree on project, source, commit, and snapshot digest.
- The starter and sealed reference compile independently with the submitted strict warning flags.
- Public tests pass 3/3 groups and sealed tests pass 6/6 groups against the reference.
- Three reviewer-authored edge groups passed for scheduler timing/PID limits, VM range and atomicity,
  and filesystem boundaries, alias staging, and unchanged-on-error behavior.
- The incomplete starter fails the public suite as documented.
- Two clean reference archive builds had identical SHA-256 digests.
- The manifest and validation prose do not overclaim ARM, sanitizer, fuzz, benchmark, transfer,
  security, review, or production evidence.

## Review limitations

- The ARM cross-compiler and QEMU were unavailable; no ARM build or boot claim is supported.
- Host sanitizer libraries were unavailable; sanitizer cleanliness is unknown.
- The upstream snapshot was outside the permitted workspace, so source/license evidence and the
  no-copy/no-paraphrase assertion could not be independently compared.
- No fuzzing, benchmarking, target-hardware, stress, security, or production assessment was run.

