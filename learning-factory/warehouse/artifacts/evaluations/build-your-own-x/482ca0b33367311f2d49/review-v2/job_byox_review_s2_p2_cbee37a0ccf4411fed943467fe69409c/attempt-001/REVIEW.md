# Independent review

Verdict: **REVISE**. The challenge is thoughtfully structured and honestly labeled `GENERATED` /
`PARTIAL`, but it is not ready for a learner-facing release. The advisory verdict does not assign a
`REVIEWED` label; only the orchestrator's acceptance validator may do that.

Priority meanings: P0 blocks release or compromises assessment integrity; P1 is a material contract
or correctness defect; P2 is a reproducibility or boundary-quality gap.

## Prioritized findings

### P0 — The learner/evaluator boundary is not enforced

The learner-facing [README](CANDIDATE/README.md) says material is revealed in stages and tells the
learner not to inspect `sealed/` (lines 10–16). [AGENTS.md](CANDIDATE/AGENTS.md) repeats that rule in
prose (lines 3–5). Nevertheless, the submitted root includes readable solution code under
`sealed/reference/`, private tests under `sealed/reference_tests/`, and evaluator answers under
`sealed/debugging/` and `sealed/review_exercises/`. Setting `PYTHONPATH=sealed/reference` made all 11
public tests pass without implementing the starter.

No deterministic student-view exporter, allowlist, view inventory, or access-control evidence is
included. If `CANDIDATE/` is distributed as the student view, the solution and grader are exposed and
progressive disclosure is an honor-system request. Publish evaluator material as a separate artifact
and validate the student view against a strict path allowlist before release.

### P1 — Layer containment and pre-mutation validation have bypasses

`LayerApplier.apply` checks only whether the final supplied destination is itself a symlink, then calls
`resolve(strict=False)` (`sealed/reference/pydocklet/layer.py`, lines 193–199). A destination such as
`alias/rootfs`, where `alias` is a symlink to an outside directory, is accepted and the payload is
written below the symlink target. This conflicts with `REQUIREMENTS.md` lines 20 and 29 and with the
evaluator answer's instruction to reject links along the destination path.

The claimed pre-mutation target validation is also incomplete. With an existing file named `blocked`,
a layer containing `.wh.victim` followed by `blocked/.wh..wh..opq` deletes `victim` and then raises
`InvalidLayer` because the opaque marker's parent is not a directory. The reference's validation loop
(layer.py lines 204–215) does not check that type before `_apply_whiteouts` mutates the tree.

Reject symlinks in the supplied destination ancestry without first adopting their resolved target,
and preflight all deterministic destination type conflicts before applying any whiteout. Add both
cases to the sealed suite.

### P1 — Image digests, publication cleanup, and immutability can diverge

Three independent probes break the image contract in `REQUIREMENTS.md` lines 36–43:

- `image.py` hashes each layer at lines 96–97, then reopens the path during application at lines
  117–119. If the file changes between those operations, the record retains the old layer digest while
  the published rootfs contains the new bytes.
- Two coordinated imports of different content to the same previously unused tag yield one success and
  one `Conflict`, but both content directories remain under `images/`. Publication happens before tag
  registration (lines 126–133), and cleanup removes only an unpublished build directory. Thus the
  failed import leaves a published object.
- Published files are returned through `ImageRecord.rootfs` with owner-writable modes. Mutating such a
  file changes the content copied into later containers while its content-addressed identity remains
  unchanged. The submission itself acknowledges that immutability is only by convention.

Hash while staging each layer into private storage and apply only that staged byte stream. Define and
enforce a safe object-claim/cleanup protocol for losing imports. Either enforce published-tree
integrity before use or narrow the learner contract so it does not promise immutability the model
cannot provide.

### P1 — The output-limit contract and public test disagree

`REQUIREMENTS.md` lines 64–66 say each captured stream is bounded to `max_output_bytes` and receives a
visible marker when truncated. `runner.py` lines 64–71 retain exactly the byte limit and append a
16-byte marker afterward. The independent probe therefore returned 21 UTF-8 bytes for a five-byte
limit. The public test explicitly expects both the five-byte prefix and the marker, so a learner cannot
both follow the literal byte bound and satisfy that test.

Specify whether the marker is bounded overhead. Prefer keeping the complete serialized result within
the configured limit (with defined behavior when the limit is shorter than the marker), then align the
test and reference implementation.

### P2 — The recorded suite needs an undeclared writable-temp assumption

With a writable `TMPDIR`, the public/reference suite passed 11/11 in the immutable submission. The
sealed suite passed 24/25 there: its CLI test constructs a scrubbed child environment without
`TMPDIR`, and `ProcessRunner` returned `EXITED/125` when `TemporaryFile` found neither writable system
temp nor writable cwd. The same 25 tests passed from a writable, content-identical copy.

This does not show that the builder's local observation was fabricated; it shows that the command is
not reproducible under the documented Python/POSIX assumptions alone. Give CLI subprocesses an
explicit writable `cwd`, make log scratch placement injectable, and record the required scratch
contract in `environment/README.md` and validation evidence.

### P2 — Artifact provenance and generated-material terms are incomplete

Manifest and provenance identity fields are internally consistent, and the linked resource is
correctly marked `NOASSERTION`. However, there is no generated-file digest inventory or generation
recipe that binds the 56 delivered files to those records. The manifest field named
`provenance_sha256` equals the source snapshot identifier, not the byte hash of `PROVENANCE.json`
(`266aadf0…`), and that distinction is not explained next to the field. The no-copy and source-license
claims could not be checked without the immutable source snapshot.

Also, “personal educational use” is not an explicit standard license for the generated challenge
material. Add a generated-artifact inventory and generator/version inputs, clarify hash semantics, and
state concrete reuse/modification terms without implying that the linked resource's unknown license
flows through.

## What held up

- The exact Python interpreter was recorded, syntax compilation succeeds, and no third-party package
  installation is needed.
- In a writable content-identical copy, all 11 public and all 25 sealed reference tests pass. The
  untouched starter fails with the documented 17 explicit TODO errors.
- The archive and subprocess code does not call `extract()` / `extractall()` or use `shell=True`.
- The pack contains only regular files and directories, and the bounded credential-pattern scan found
  no match.
- The conceptual material, staged TODOs, design questions, non-goals, and production caveats are useful
  and unusually candid. The submission does not claim fuzzing, benchmarking, transfer verification,
  productionization, or genuine process confinement.

The P0/P1 findings require revision even though the existing suites pass under their expected local
conditions.
