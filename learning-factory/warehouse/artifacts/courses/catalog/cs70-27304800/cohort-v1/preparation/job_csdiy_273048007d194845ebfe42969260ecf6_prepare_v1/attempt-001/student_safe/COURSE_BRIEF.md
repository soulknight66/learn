# UCB CS70 Engineering Kickoff

**Artifact status:** `PREPARED_NOT_VALIDATED`  
**Unit:** `kickoff_01_stable_matching_engineering`  
**Expected effort:** about 8 hours

## What this is

This is a bounded, manager-authored kickoff for a strong algorithms learner who wants more practice turning mathematics into reliable software. The catalog describes CS70 as a discrete mathematics and probability course and connects logic and proof with stable matching. This unit uses that single correspondence as its starting point.

This packet is not an official UC Berkeley lesson or assignment. It does not reproduce the cataloged course, and completing it cannot establish completion of CS70. The course website and linked repository were not fetched; the textbook and assignments were not supplied. Everything you need for this kickoff's problem statement is defined below and in `STUDY_TASK.md`.

## The model

There are two disjoint groups, called `left` and `right`, of the same finite size. Every participant has a **strict, complete preference order** over every participant in the opposite group. A matching pairs each left participant with exactly one right participant and vice versa.

For a matching (M), an unmatched-together pair ((l, r)) is a **blocking pair** when both conditions hold:

1. (l) ranks (r) above the partner assigned to (l) by (M); and
2. (r) ranks (l) above the partner assigned to (r) by (M).

A matching is **stable** if it has no blocking pair.

In this unit, the left side proposes. Your implementation will use deferred acceptance under the assumptions above. You are expected to connect its proof obligations to concrete program state and tests, not merely produce a plausible matching.

## Why this is an engineering task

The mathematical theorem assumes well-formed preference orders and often treats representation details as invisible. A software component cannot. It must decide how identifiers are represented, how invalid rankings fail, whether inputs are mutated, what deterministic output means, and how a caller can reproduce a result.

Your work should keep three layers distinct:

- **Model:** the valid instance and the definition of stability.
- **Implementation:** state, invariants, transitions, and termination.
- **Evidence:** an independent checker, automated tests, proof arguments, and run instructions.

That separation is the central software-engineering theme of this kickoff.

## Learning goals

By the end of the unit, you should be able to:

- express mathematical assumptions as a precise API contract;
- implement deterministic left-proposing deferred acceptance without mutating caller-owned input;
- relate loop invariants to matching safety and progress;
- justify termination, stability, proposer optimality, and asymptotic bounds;
- test semantic properties with an oracle that does not reuse the implementation's decision logic; and
- explain how the simplified model differs from a production matching service.

## Scope boundary

Stay within one-to-one matching with equal-sized groups and strict, complete rankings. Ties, incomplete lists, capacities, unacceptability, strategy, fairness policy, persistence, concurrency, privacy, and deployment are valuable later topics, but they are not implementation requirements here. You will discuss one extension without building it.

The catalog also mentions graph theory, number theory, polynomial rings, coding theory, probability, hashing, and load balancing. Those topics remain unplanned. No sequence or completion credit for them is implied by this kickoff.

## Working sequence

1. Read this brief and the complete task before coding.
2. Write the public contract and choose a small, explicit representation.
3. Implement input validation and deferred acceptance.
4. Build a definition-based stability oracle separately from the algorithm.
5. Add deterministic examples, malformed-input tests, and generated-property tests.
6. Write the proof and complexity arguments, then run the project from a clean checkout using only your documented command.
7. Answer `COMPREHENSION.md` in your submission.

Do not seek or use an official assignment to fill gaps in this task. If you consult any optional public source, cite it, identify exactly what it influenced, and ensure your submission remains your own work.

---

**Provenance:** Course-manager-authored from the supplied CSDIY catalog snapshot at source commit `adce8e13789dc16aa6d1fbe163e9541736defae4`, source file `docs/数学进阶/CS70.en.md`, catalog content SHA-256 `9542f4ac4a33e63d6be53a59373f1d6a02e96bea16cf1bb645474db72c15d449`. No external material was retrieved.
