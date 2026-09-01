# Self-check

This reflection answers the supplied questions. It is local self-review, not an assessment result.

## 1. Source facts versus generated practice

The supplied normalized record identifies an official MIT 6.858 Lab 1 unit and gives only a
catalog-level Zoobar/buffer-overflow theme. The `frameguard` contract, layout, Python code, tests,
threat model, and reports are newly authored practice material. No official lab specification,
starter repository, tests, environment, or lecture material was available.

## 2. Region invariants

Data occupies `[0,16)` and begins as sixteen zero bytes. Role is index 16, begins as `0x00`, and
grants exactly when equal to `0x01`. Canary occupies `[17,24)` and must equal `FRAMEOK` to be intact.
The whole frame is exactly 24 bytes. The hardened path may mutate only data on an accepted request;
rejections leave all regions initial.

## 3. Two boundaries

Sixteen bytes is the application security boundary: the next byte is authorization metadata.
Twenty-four bytes is the emulator's outer capacity: it prevents the Python copy model from leaving
its represented frame. An input of length 17 through 24 is within emulator capacity but has already
crossed the application boundary.

## 4. Shortest reaches and test evidence

Length 17 first reaches role because its last copied index is 16. Length 18 first reaches canary
index 17. Tests use the same generic ordered copy, try three different 16-byte prefixes followed by
`0x01`, explicitly exercise canary change, and table-drive every length from 0 through 25. Thus the
result derives from offsets rather than a special-case payload branch.

## 5. Grant with intact canary

Yes. A 17-byte vulnerable input can set role to `0x01`, while canary begins at the next index and
remains `FRAMEOK`. Therefore canary integrity cannot serve as the authorization defense; it detects
only some later corruption and does not prevent use of an already-corrupted role.

## 6. Proof of rejection before mutation

The focused hardened test substitutes a trackable fresh frame, snapshots all 24 initial bytes, and
wraps `_copy_bytes` with a spy. A 17-byte request returns rejected, the spy has zero calls, and the
entire frame still equals its snapshot. Copying first and repairing only role would change the data
prefix and call the spy, so it would fail this test.

## 7. Frame-reuse detector and threatened property

`test_requests_are_isolated_after_authorization_change_and_rejection` first makes a vulnerable call
that grants access, then checks that an empty call denies with an intact canary. It also follows an
oversized rejection with an empty call and repeats the check after a hardened rejection. Accidental
reuse would threaten request isolation and could turn prior attacker-controlled metadata into a
later authorization-integrity failure.

## 8. Diagnostic utility and residual inference

Lengths, fixed reason codes, accepted/access flags, overflow counts, and integrity flags can answer
whether failures cluster at a boundary, which path rejected, whether canary corruption was observed,
and whether access was granted. They do not reveal direct content. Exact lengths, timing/correlation
outside this model, rare reason patterns, and access outcomes could still identify workflows or
usage patterns; coarse aggregation and bounded retention reduce that risk.

## 9. Policy, mechanism, and presentation

`_role_allows_access` is policy. `_fresh_frame` and `_copy_bytes` are layout/copy mechanisms, while
the two request functions choose validation policy and orchestration. `_observation` and immutable
`Observation` are diagnostic presentation; they expose selected metadata without retaining a frame
or payload.

## 10. Properties outside the model

The exercise says nothing conclusive about native allocation, undefined behavior, stack direction,
C ABI, compiler defenses, ASLR, control-flow attacks, concurrency, resource exhaustion, HTTP
parsing, sessions, authentication, persistence, monitoring, deployment, or overall web-application
security. Its fixed canary is not a secret randomized production canary.

## 11. Reproducible evidence versus interpretation

Another local runner can inspect the submitted bytes, recompute the six SHA-256 digests, rerun the
exact `unittest` command, and observe the 13 test cases and metadata outcomes. The threat assessment,
choice to prefer rejection, observability recommendations, and claims about what the abstraction
teaches are reasoned interpretations. The report is learner-captured evidence, not independent
examiner validation.

## 12. Unjustified claims after passing tests

Passing all local tests would still not justify claims that a native program or Zoobar is secure,
that every implementation of the idea is safe, that hidden/official requirements were met, that I
completed official MIT Lab 1, that learning transferred to another system, or that I completed the
course. Those prerequisites and validations were unavailable.
