# Examiner Rubric — Unit 01 Deterministic Triangle Rasterizer

## Control status and provenance

This examiner-only rubric evaluates the manager-authored Unit 01 packet for course `course_05e1e7c8db8ac31e5a75e00fc94f7bad`. It is independent of learner prose claims and is not an institutional CMU rubric. It derives its scope from the catalog-declared topics of sampling, rasterization, interpolation, and geometric transformations at CSDIY commit `adce8e13789dc16aa6d1fbe163e9541736defae4` (catalog content SHA-256 `2f655898fdcf113cd550988459ad49d2a54867ac8164528c2989364618aee451`). No remote material was retrieved.

**Rubric label:** `EXAMINER_ONLY_PREPARED`  
**Result before controlled evaluation:** `UNVALIDATED`  
**Maximum claim:** Unit 01 completion only; never course completion

## Independent evaluation procedure

Evaluate the submitted revision, not its evidence log alone.

1. Record the immutable revision or artifact digest and evaluation environment.
2. Start from a clean out-of-source build directory and run configure, build, and CTest without network access.
3. Run examiner-owned scenes and malformed inputs that are not copied from learner tests. Inspect exit statuses, diagnostics, complete PPM structure, pixel bytes, and whether failed outputs are absent or clearly incomplete.
4. Exercise the core library directly where its public interface permits. Run the submitted suite at least twice and compare observable results.
5. When supported by the toolchain, run relevant tests with address/undefined-behavior sanitizers. Record unsupported sanitizer execution rather than silently treating it as passed.
6. Review source, tests, README, engineering notes, comprehension responses, and captured evidence. Recompute all substantive claims that affect scoring.
7. Store validator-produced logs and the final label in durable job evidence.

Do not retrieve the catalog's website, playlist, assignments, or commercial materials to grade this unit; the local contract is authoritative for this manager-authored exercise.

## Critical gates

All gates are required for a completion label:

- The submitted source configures and builds offline with the documented C++17 commands.
- The produced executable accepts the specified CLI and a valid `RSCENE1` file and emits a structurally valid deterministic P6 image.
- Examiner checks find no crash, out-of-bounds access, or unbounded allocation on the required adversarial inputs.
- Both input windings are supported and a shared edge does not create a crack or double ownership.
- No examiner-only material or copied rubric appears in learner-facing deliverables.
- The evaluator can trace the result to validator-produced evidence for the submitted revision.

If any gate fails, report `UNIT_01_NOT_COMPLETE` regardless of points. A successful gate check does not waive deficiencies in the scored criteria.

## Scored criteria (100 points)

### A. Rasterization behavior — 45 points

- **Pixel-center coverage and clipping (10):** Coverage uses `(x + 0.5, y + 0.5)`, examines only a safely clipped bounding region, and agrees with independently calculated inside/outside/boundary cases.
- **Winding and shared-edge ownership (10):** Reversing attributed vertex order preserves output. Examiner-owned adjacent-triangle cases assign every shared-edge sample once, including horizontal, vertical, and diagonal configurations.
- **Interpolation and byte conversion (9):** Affine barycentric RGB values correspond to the covered sample, channels are clamped, and `floor(255*c + 0.5)` is applied consistently.
- **Scene ordering and special geometry (8):** Background, later-triangle overwrite, wholly/partly off-screen geometry, exact degeneracy, and finite skinny triangles follow the contract and summary counts.
- **PPM and repeatability (8):** Header and payload length/order are exact; repeated runs have identical bytes and stable summaries with no volatile fields.

### B. Input, failure, and implementation engineering — 25 points

- **Strict bounded parser (7):** Header order, token counts/types, range checks, finite-number checks, comments, record limit, truncation, and unknown records are handled without accepting ambiguous tails.
- **Arithmetic and memory safety (5):** Size calculations are checked before allocation; indexing and conversions avoid undefined behavior; examiner adversarial runs and available sanitizers find no defect.
- **Failure semantics (4):** Argument, parse, input-I/O, and output-I/O failures are nonzero, diagnostic, and do not leave a new success-looking output.
- **Architecture and build hygiene (5):** A reusable core is separated from parsing/CLI/PPM concerns, global mutable state is absent, tests call the core, warnings are enabled, and builds are offline/out-of-source.
- **Documentation and evidence integrity (4):** README commands work; engineering notes accurately document invariants, complexity, numeric choices, rejected design, and scope; the evidence log corresponds to the submitted revision but is not treated as self-validating.

### C. Test quality — 20 points

- **Behavioral examples (7):** Assertions inspect exact statuses, ownership, pixels, summaries, and PPM structure for the required basic and overlap cases.
- **Boundary and failure cases (6):** Required off-screen, degenerate/skinny, malformed/range/size, truncated/unknown, and output-failure paths are automated and meaningful.
- **Property-oriented checks (5):** Fixed-seed cases test winding invariance and bounded writes with a useful oracle and reproducible failure report; cases vary geometry rather than repeating one fixture.
- **Reproducibility and independence (2):** CTest runs cleanly twice, tests do not depend on network, working-directory accidents, wall clock, or test order, and generated scratch files are isolated.

### D. Comprehension — 10 points

Award against the learner's own code and cited evidence:

- **Coverage and interpolation reasoning (3):** Accurately connects orientation normalization, boundary ownership, affine weights, weight sum/reconstruction, and attribute-preserving winding changes.
- **Complexity and numerical judgment (2):** Gives a sum-of-clipped-bounding-box cost (with framebuffer bounds) and explains why a scale-blind epsilon can erase valid geometry or preserve unstable cases.
- **System and failure trace (2):** Correctly locates parsing, core, conversion, and I/O boundaries and traces nonzero failure without treating partial output as success.
- **Testing and evolution (3):** Describes a genuine generated-input property and its limits, then identifies stable core contracts and staged changes for depth and perspective-correct interpolation.

## Scoring decisions and caps

- A submission that does not build receives at most 20 points and fails the gates.
- A submission that builds but cannot render a valid scene receives at most 35 points and fails the gates.
- Missing or ineffective automated tests cap the result at 75 points.
- Missing comprehension responses cap the result at 90 points.
- Unsupported extra features earn no points and defects they introduce count normally.
- Use zero for absent evidence; do not infer behavior from intent or comments.

The passing threshold is **80/100 plus every critical gate**. A controlled validator may then record `UNIT_01_COMPLETE` with durable evidence. It must leave the course status as not complete.

## Result record

The examiner should record: submission digest/revision, commands, toolchain, test and sanitizer outcomes, gate decisions, criterion scores with concrete observations, total, validation label, and artifact locations. The only positive label authorized by this rubric is `UNIT_01_COMPLETE`; it conveys no credit for unprepared course units.

