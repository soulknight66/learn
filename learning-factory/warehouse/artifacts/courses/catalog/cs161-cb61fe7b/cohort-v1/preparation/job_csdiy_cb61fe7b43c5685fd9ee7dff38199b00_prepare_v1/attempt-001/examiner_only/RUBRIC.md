# Independent Rubric: Security Boundaries and Fail-Closed Authorization

This rubric is examiner-only. Assess the learner artifacts and observed behavior independently; learner claims and pasted command output are leads, not proof. Run examiner-controlled tests in a disposable copy of the submission.

## Validation procedure

1. Confirm the submitted scope is a Go library and does not depend on external services or fetched course material.
2. Run `gofmt` inspection, `go vet ./...`, `go test ./...`, and `go test -race ./...` with bounded timeouts.
3. Adapt black-box examiner tests to the documented public API. Do not rely solely on learner tests.
4. Inspect state before and after denied operations, mutate input/output slices, inject identifier collisions, and coordinate concurrent operations with barriers.
5. Compare documentation, comprehension reasoning, code, and observed behavior. Score the observed result.

## Critical caps

- No runnable implementation or a package that does not compile: maximum 20 points.
- Any reproducible path for a non-owner to replace, grant, revoke, or delete, any read by an unrelated principal, or a completed revoke followed by a newly started successful read: maximum 55 points.
- A data race in security-relevant state, overwrite on identifier collision, or caller slice mutation that changes stored content: maximum 70 points.
- Fabricated evidence or a claim that this component supplies out-of-scope authentication, confidentiality, persistence, or complete secure file sharing: maximum 70 points.

Apply the lowest relevant cap after calculating the raw score.

## Scoring (100 points)

### 1. Threat model and design reasoning — 15 points

- 5: Assets, security goals, actors, attacker capabilities, trusted identity boundary, and mutable-data boundary are concrete and internally consistent.
- 4: At least four meaningful abuse cases connect a failure mode to both a mitigation and a verification method; authorization, aliasing, and concurrency/state transition are represented.
- 4: Authorization table, state invariants, public error policy, linearization points, byte ownership, and identifier strategy agree with the implementation.
- 2: Authentication, network security, persistence, encryption, and production deployment limits are stated without overclaiming.

### 2. Authorization and lifecycle behavior — 25 points

- 4: Create establishes exactly one owner, a fresh identifier, owned payload bytes, and no unintended grants.
- 4: Read succeeds only for owner or currently granted reader and returns the correct current content.
- 4: Replace is owner-only, atomic, and preserves the intended grant set.
- 7: Grant and revoke are owner-only; documented repeat behavior is deterministic; revoke has the required happens-before property.
- 4: Delete is owner-only and makes every later operation on that identifier fail without retaining usable access.
- 2: Unhandled roles and states deny by default.

### 3. Fail-closed errors and representation safety — 15 points

- 5: Existing-inaccessible, unknown, and deleted identifiers share one public denial classification for syntactically valid requests; returned details do not reveal existence.
- 4: Denied and failed mutations leave payload, owner, grants, and document population unchanged.
- 4: Both input and output byte slices are defensively copied; examiner mutation probes pass.
- 2: Malformed input is handled without panic, partial mutation, payload disclosure, or sensitive logging.

### 4. Concurrency and identifier robustness — 12 points

- 7: Shared state is race-free; documented linearization points match locking; barrier-based examiner histories preserve policy, especially revoke/read and delete/read.
- 5: Production IDs use `crypto/rand` with at least 128 bits, opaque encoding, and collision retry or explicit safe failure; controlled collision testing cannot overwrite a document.

### 5. Verification quality — 18 points

- 5: Table-driven or equivalent tests cover all six operations across owner, granted-reader, and unrelated roles.
- 4: Transition tests cover grant, repeat grant, replace, revoke, repeat revoke, delete, and requests after deletion.
- 3: Tests detect existence-oracle error divergence, slice aliasing in both directions, and collision mishandling.
- 3: Concurrency tests use explicit coordination rather than sleeps and pass under the race detector.
- 3: A deterministic randomized, model-based, or fuzz test checks a meaningful state or authorization invariant and has a reproducible failure path.

### 6. Comprehension — 10 points

- 5: Responses 1–4 correctly reason about trusted identity, observable errors, representation aliasing, and revoke linearization using the learner's implementation.
- 5: Responses 5–8 distinguish identifier unpredictability from authorization, explain collision safety and atomic denial, and identify credible new boundaries for a networked persistent system.

### 7. Engineering evidence and maintainability — 5 points

- 2: Evidence records tool version, exact commands, exit status, and relevant output without converting failures into success claims.
- 2: The invariant-to-test map is accurate when spot-checked against examiner results.
- 1: Code is formatted, narrowly scoped, idiomatic enough to review, and free of unnecessary dependencies or nondeterministic sleep-based tests.

## Decision

Issue `PASSED` only for a final score of at least 80, with no critical-cap condition and successful examiner-controlled normal and race-enabled test runs. Otherwise issue `NEEDS_REVISION` with observed counterexamples and the affected criteria. This decision applies only to the kickoff unit and never to the complete catalog course.
