# Independent Rubric: Buffer-Pool Engineering Kickoff

This file is examiner-only. Evaluate the durable submission and observed command results, not the learner's claim of completion. Do not infer completion of an official CMU assignment or of CMU 15-445 from this result.

## Validation procedure

1. Confirm that the six required submission files are present and that no generated build tree, credential, external solution, or downloaded course repository is being used as evidence.
2. From `submission/`, run a clean configure, build, and CTest invocation using the commands in the task. Capture exit status and output.
3. Inspect tests before implementation details. Confirm that the page-store double records calls and injects selected failures deterministically.
4. Add or run examiner-controlled probes for edge cases the submitted suite might miss. Keep those probes outside learner-visible artifacts.
5. Inspect the implementation and notes for each scored claim. A comment or prose assertion earns no functional points when observable behavior contradicts it.
6. Score comprehension responses against the submitted implementation, not against an imagined design.

## Score: 100 points

### A. Reproducibility and bounded scope — 10 points

- **4:** The prescribed clean CMake build succeeds without network access; CTest discovers and runs the test executable.
- **3:** The required layout is complete, warnings are sensibly enabled, and no generated/downloaded material is required.
- **3:** The implementation remains a standalone C++17 microcomponent and does not misrepresent itself as BusTub or an official course assignment.

### B. Contract, representation, and invariants — 15 points

- **4:** Public operations expose success and distinct failure conditions sufficiently for deterministic use and testing.
- **4:** Ownership and access lifetime are safe and documented; ordinary use cannot retain an unexplained dangling frame reference.
- **4:** Notes identify at least four meaningful invariants, including unique residency, capacity, pin non-underflow, and recency/residency consistency, and connect them to transition sites.
- **3:** The store boundary is injected rather than hidden behind real I/O or global state; staging/failure policy is documented accurately.

### C. Functional correctness — 30 points

- **5:** Construction and ordinary fetch behavior are correct: zero capacity is rejected, misses read once, hits do not read, duplicate residency is impossible, and every successful fetch increments the pin count.
- **7:** Replacement is deterministic LRU by successful fetch among unpinned residents. Re-fetch changes recency; writes and unpins do not; pinned pages are never victims.
- **4:** An all-pinned miss returns an error with no pool mutation and no store call. Invalid write and unpin operations likewise avoid partial mutation and underflow.
- **6:** A valid write changes the latest bytes and dirtiness. Clean eviction does not write; dirty eviction writes the latest bytes before replacement; successful flush cleans exactly the intended resident page.
- **8:** Store failures preserve the required in-memory state. Failed flush remains dirty; failed read does not consume a free frame or victim; failed dirty-victim write prevents the requested read; successful victim write followed by failed requested read leaves the old victim resident and dirty while permitting the completed store side effect.

Award partial credit within each item only for behavior demonstrated by repeatable evidence. For the prompt 1 trace, the expected final residents are pages 10 and 30 in LRU-to-MRU order, page 20 is evicted, page 10 remains dirty, and no write-back is required by that sequence. The store still has `10: "A"`, `20: "B"`, `30: "C"` unless the learner explicitly performs an out-of-contract extra flush.

### D. Test quality — 20 points

- **5:** Tests cover zero capacity, hit/miss store-call counts, multiple pins with balanced unpins, invalid writes/unpins, and capacity/uniqueness checks.
- **5:** Tests distinguish LRU from FIFO or arbitrary replacement by re-fetching a resident, and independently show that pinned pages are ineligible and an all-pinned miss is side-effect-free.
- **5:** Tests distinguish dirty and clean eviction, verify latest persisted bytes, and cover successful and failed explicit flush.
- **5:** Tests inject all required failure positions, including write-success/read-failure, and include a longer deterministic mixed sequence with invariant checks after operations. Assertions diagnose the failed property rather than only returning a generic nonzero status.

### E. Engineering quality and analysis — 15 points

- **4:** Code has clear responsibilities, avoids avoidable global state and ownership hazards, and uses types/names consistently.
- **4:** Observable operations meet the requested expected-time targets, or a small deviation is precisely measured and justified; space is bounded in terms of capacity and stored page bytes.
- **4:** State is committed only after prerequisite fallible work. Error paths remain valid and retriable without ad hoc repair.
- **3:** Notes give exact commands, an accurate limitation, and a credible alternative design with a concrete trade-off.

### F. Comprehension — 10 points

- **2:** Prompt 1 gives a consistent stepwise trace and correct store-call accounting, tied to test evidence.
- **1:** Prompt 2 identifies pin count one after three fetches/two unpins, continued eviction ineligibility, and a concrete underflow defense.
- **2:** Prompt 3 distinguishes the two failure positions. On write failure, page 1 stays resident/dirty and page 2 is not read. On subsequent read failure, page 1 still stays resident/dirty, while the successful write may persist its latest bytes. Retry reasoning is coherent.
- **1:** Prompt 4 separates a universal transition invariant from finite example coverage and proposes a sequence capable of exposing distinct failures.
- **1:** Prompt 5 accurately describes the submitted ownership/lifetime policy and a real alternative trade-off.
- **1:** Prompt 6 derives complexity from actual structures and spots a target-breaking convenience choice such as a linear recency scan on each hit.
- **1:** Prompt 7 gives a plausible interleaving, affected shared state, and synchronization boundary without claiming thread safety was implemented.
- **1:** Prompt 8 preserves the kickoff/course boundary and names at least three useful missing facts, such as a selected semester, exact official prompt, immutable starter commit, lawful access/license, official ordering, or worker-controlled validation contract.

## Critical caps and decision

- If the prescribed build does not compile for submission-caused reasons, cap the score at **55**.
- If CTest runs no meaningful automated test, cap the score at **60**.
- If a pinned page can be evicted, pin counts can underflow through the public API, or a successful-path dirty eviction loses the newest bytes, cap the score at **69**.
- If examiner observation shows tests or notes describe behavior from a materially different code version, score only the observed submission and cap at **69**.

The kickoff unit passes at **75/100 or higher** with no active cap below 75. Record the commands, outputs, score breakdown, and cap decisions as validator evidence. A pass applies only to `unit_kickoff_buffer_pool_engineering_v1`; it must not promote the whole course or any official CMU unit to complete.
