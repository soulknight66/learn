# Independent review

## Verdict

**PASS (advisory).** I found no blocking correctness, learner-usability, provenance-boundary, or validation-honesty defect. The reference implementation satisfies the documented bounded model in the exercised paths, and fresh independent runs reproduced the builder's relevant results. This verdict does not publish `REVIEWED`; only the orchestrator-controlled acceptance validator may do that.

## Prioritized findings

### P0/P1 — No blocking findings

The API, requirements, reference implementation, and answer material agree on scheduler cursor history, legal transitions, PID reuse, VM frame accounting and zeroing, RAMFS bounds and overlap behavior, and error atomicity. Strict supplied tests plus an independent edge-case probe all passed against the reference.

### P2 — Default static archives are not byte-reproducible

Two clean reference builds produced identical hashes for every `.o` member but different `libmicaos.a` hashes (`3775eb5c...` versus `37f2305b...`). `ar tv` showed host owner/group and build-time metadata, and the Makefile invokes GNU ar 2.30 with `rcs` rather than deterministic mode.

This does not contradict a candidate claim: no bit-reproducible binary is claimed, build products are scratch artifacts, and both behavior and object code reproduced. If downstream provenance relies on checksumming archives, use a deterministic ar mode such as `rcsD` after confirming toolchain portability, or normalize/archive the outputs in the worker harness.

### P2 — Learner isolation remains an external transfer gate

Progressive disclosure is well structured: the main README leads through requirements, concepts, milestones, public tests, debugging symptoms, and review prompts, while reference code, full tests, diagnoses, and answers live below `sealed/`. Learner-facing build rules do not consume sealed material.

The master candidate necessarily contains both trees, however, and no worker-harness student-view export was supplied here. The orchestrator must exclude `sealed/` from the learner view. The candidate is honest about this limitation and does not claim `TRANSFER_VERIFIED`.

### P3 — Upstream non-copying provenance was not externally corroborated

`MANIFEST.yaml`, `PROVENANCE.json`, and `LICENSE_BOUNDARY.md` consistently identify the CC0 catalog metadata, mark the linked tutorial license as `NOASSERTION`, state that linked content was not copied, and avoid granting rights to that linked resource. Only provenance URLs occur elsewhere in the pack.

The upstream snapshot and linked tutorial were inaccessible in this workspace, so textual independence could not be compared externally. The generated-material statement is also a usage boundary rather than an SPDX license grant; downstream redistribution should not infer broader rights from it.

## Correctness and reproducibility evidence

- The incomplete learner starter builds cleanly and predictably reports `4 passed, 3 failed` at the marked TODO paths.
- The sealed reference suite passes with strict C11/freestanding core flags and at `-O2`.
- The public suite independently linked to the reference reports `7 passed, 0 failed`.
- An independent probe passed PID maximum wrap, reaping and slot reuse, historical-cursor behavior, VM exhaustion/isolation/zero reuse, read-only rejection, bounded name validation, full-size and overlapping writes, and state preservation after rejection.
- Extra GCC warning families produced no diagnostics, and the core archive has no undefined symbols under `nm -u`.
- The supplied Make targets and behavioral results are reproducible in a writable copy; only byte identity of the archive container is not.

## Learner usefulness and disclosure

The pack is unusually clear about its scope: it teaches three deterministic in-memory kernel-shaped state machines, not a bootable or production OS. The observable contract is precise, the starter has localized TODOs, the public tests provide early feedback without exhausting the specification, and the milestone questions encourage contract reasoning rather than test memorization. Sealed review and production notes accurately explain tradeoffs and limitations.

The exercise's relationship to the catalog title is narrower than a real “OS from scratch,” but that narrowing is disclosed repeatedly and avoids misleading the learner about boot, hardware, privilege, persistence, or security capabilities.

## Validation honesty

The manifest remains `GENERATED` with exactly `GENERATED` and `PARTIAL`, requires independent validation, and sets `productionized` to false. Candidate prose calls its evidence worker-local, lists missing tools and unperformed checks, and explicitly disclaims all stronger labels. My runs reproduced the current build/test claims. Historical claims involving absent `PRIOR_BUILD` and `PRIOR_REVIEW` remain unverified rather than being treated as evidence.

## Residual limitations

Only GCC 8.5.0 was usable. Sanitizer runtimes, a second compiler, the named static analyzers, Valgrind, emulators, and NASM were unavailable. I did not perform fuzzing, benchmarking, cross-target, hardware, concurrent, production, or transfer validation. These limitations are recorded in `EVALUATION.json` and `VALIDATION.md` and do not promote any corresponding label.
