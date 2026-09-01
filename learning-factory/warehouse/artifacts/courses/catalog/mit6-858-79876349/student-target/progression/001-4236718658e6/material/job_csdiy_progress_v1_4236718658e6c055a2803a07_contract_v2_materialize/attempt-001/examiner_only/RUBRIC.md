# Examiner rubric: bounded byte-frame practice task

## Authority and scope

This rubric applies only to learner work produced for the agent-generated task associated with `unit_8b2011001dc8b37c0dff9f1dd438e897`. The normalized record retains classification `explicit_official_course_unit`, while its official specification and supporting materials remain unavailable. Do not award or imply MIT Lab 1 credit, broader transfer, or course completion.

Treat prose claims as leads, not evidence. Re-run the submitted tests from a clean local process, inspect the implementation, recompute a sample of reported hashes, and record commands, streams, exit statuses, and observations. Do not use a network or disclose this file or `NOVEL_CHECK.md` into `student_safe/`.

## Critical gates

A submission cannot pass if any of these conditions holds:

- the implementation or required documents are absent or cannot be inspected;
- the examiner cannot run the standard-library test suite locally;
- the hardened path can mutate the frame before rejecting an overlength payload;
- an overlength input can grant access through the hardened path;
- requests share mutable frame or decision state;
- the learner uses a live target, network access, unsafe native-memory interface, copied restricted content, or examiner-only material;
- raw payload bytes are emitted or persisted by the package diagnostics; or
- the submission claims official lab credit, demonstrated transfer, or course completion.

Ordinary defects may receive `REVISE`; unsafe scope violations, fabricated evidence, or pervasive nonfunctionality warrant `FAIL`.

## Scored criteria (100 points)

### 1. Boundary and provenance discipline — 8 points

- 4: Accurately distinguishes the official-unit record classification from the unavailable official lab material and the newly authored task.
- 4: Keeps execution local, observes the stated safety boundary, and limits all completion claims.

### 2. Vulnerable semantic model — 20 points

- 5: Fresh frame is exactly 24 bytes with zero data, role `0x00`, and `b"FRAMEOK"` at the declared offsets.
- 5: Lengths 0 through 24 copy sequentially from index 0 without enforcing the 16-byte data boundary.
- 5: Authorization is a separately inspectable pure decision that grants exactly for role byte `0x01`.
- 5: Observations, overflow counts, canary checks, and the over-24 capacity result match the public contract.

Expected landmarks include: a suitable 17-byte input can change the role and grant access while leaving the canary intact; a suitably chosen input reaching index 17 changes the canary; length 24 is modeled, while length 25 is rejected as `MODEL_CAPACITY_EXCEEDED` without copying.

### 3. Hardened path and isolation — 20 points

- 8: Validates `len(payload) <= 16` before copy and rejects every longer value with `PAYLOAD_TOO_LONG` and no partial mutation.
- 4: Accepted data never changes role or canary and never grants access.
- 4: Non-`bytes` values raise `TypeError` before frame construction or mutation on both paths.
- 4: Every request uses fresh state, including after a granting vulnerable request and after rejection.

### 4. Deterministic test quality — 15 points

- 7: Covers all required partitions and exact observations, with assertions capable of detecting plausible wrong implementations.
- 4: Includes meaningful table-driven coverage and tests pre-validation rather than post-copy repair.
- 4: Uses only deterministic standard-library tests and passes under the declared command in a fresh process.

Do not award full credit for tests that merely mirror implementation helpers or omit negative assertions.

### 5. Threat model and design reasoning — 15 points

- 6: Connects assets, actors, boundary, abuse path, and distinct integrity, availability, and privacy properties coherently.
- 5: Explains component separation, fail-closed ordering, rejection-versus-truncation, and request isolation.
- 4: Correctly limits canary claims and identifies at least two material gaps between this emulator and native or deployed software.

### 6. Reproducibility and debugging evidence — 7 points

- 3: Report inventory, command, status, count, hashes, redacted trace, label, and claim boundary are specific and internally consistent.
- 4: Debug entries contain genuine hypotheses, experiments, observations, and decisions addressing a security invariant and privacy or isolation.

### 7. Novel check — 15 points

Administer `NOVEL_CHECK.md` only after freezing the submitted artifacts. Score it using that file's landmarks. Do not permit code edits during the check.

## Outcome rule

- `PASS`: at least 80 points, every critical gate satisfied, at least 12/20 in each of criteria 2 and 3, and at least 8/15 on the novel check.
- `REVISE`: work is safely in scope and substantially inspectable, but a gate that can be corrected, a threshold, or required evidence is missing.
- `FAIL`: unsafe or dishonest conduct, prohibited material use, or work too incomplete to evaluate.

Report the score, outcome, exact evidence inspected, independently observed command results, uncertainties, and remediation if applicable. Label the verdict `INDEPENDENT_EVALUATION_OF_GENERATED_PRACTICE_TASK_ONLY`.
