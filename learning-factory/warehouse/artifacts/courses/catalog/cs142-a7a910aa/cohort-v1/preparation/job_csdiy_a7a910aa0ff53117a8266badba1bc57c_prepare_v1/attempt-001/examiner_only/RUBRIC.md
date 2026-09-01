# Independent Examiner Rubric — Algorithm Run Log Kickoff

## Scope and authority

Apply this rubric only to `manager_unit_01_algorithm_run_log`. A passing result supports the claim **KICKOFF_UNIT_COMPLETED** and never a claim that Stanford CS142, its projects, or any larger course has been completed.

Do not accept the learner's README, screenshots, prose, or claimed test output as proof by itself. Inspect the submitted files, run the tests in a clean process, and exercise the browser behaviors. Record evidence for every awarded section.

## Evaluation procedure

1. Confirm that the reviewed files are confined to the learner submission and contain no examiner-only material.
2. Run `node --test submission/tests/*.test.mjs` from the attempt root. Record the command, exit status, and test counts.
3. Serve or open the page in a way that supports ES modules without modifying the submission. Use a fresh storage key state for the normal-flow check.
4. Inspect the module boundaries and test source; a green suite does not establish untested behavior.
5. Perform the specified browser checks, including hostile display text, malformed storage, keyboard operation, and narrow layout.
6. Score the implementation evidence and the comprehension responses independently, then apply the critical gates and caps.

## Critical gates

All gates must pass before the unit can pass:

- The page and automated test suite both execute without adding a third-party dependency or making a network request.
- Accepted data and restored data are validated; no obvious path renders an algorithm name as executable markup.
- Malformed initial storage does not cause an uncaught failure and is not silently overwritten merely by loading the page.
- The submitted tests are substantive learner tests, not empty, skipped wholesale, or hard-coded output.
- No solution, rubric, hidden validator, secret, or another learner's material has been copied into the learner submission.

If a gate fails, record the numerical score for diagnosis but set the result to `NOT_YET_COMPLETE`.

## Scoring (100 points)

### A. Observable behavior — 25 points

- **5:** Valid form submission creates exactly one normalized record, clears the form, persists state, and updates the view.
- **5:** Invalid input yields useful field-specific feedback, preserves entered values, and changes neither in-memory nor stored state.
- **4:** Display ordering follows ascending `n`, algorithm name, then `id`, including full ties.
- **3:** Removal targets one identifier, persists the result, and behaves safely if the identifier is absent.
- **3:** Count and minimum-time summaries are correct, with an explicit nonnumeric empty state.
- **3:** Reload restores valid data; missing, malformed, and structurally invalid storage follow the specified distinct load contract and recovery behavior.
- **2:** Markup-like names appear literally and the required flow works without external resources.

Award a line only for observed behavior, not for the presence of similarly named functions.

### B. Architecture and contracts — 18 points

- **6:** Domain validation, immutable transitions, ordering, and summary logic are cohesive and free of DOM, storage, clock, random, and network dependencies.
- **4:** The storage adapter has an explicit, testable contract that distinguishes absence, success, and invalid/corrupt data without silently repairing on load.
- **4:** The browser controller composes boundaries cleanly; dependency direction and state ownership are understandable.
- **4:** Public return shapes, identifier injection, storage key, invariants, and error behavior are documented and consistently implemented.

Deduct up to all points on an item for shared mutable state, validation duplicated inconsistently at several layers, or hidden browser dependencies in otherwise pure modules.

### C. Automated tests — 22 points

- **7:** Validation tests cover all four field contracts, boundary values, normalization, and multiple simultaneous errors.
- **5:** Transition tests cover insertion, duplicate identifiers, existing/missing removal, and non-mutation of caller-owned arrays and objects.
- **4:** Ordering tests force every key and include a complete tie-break; summary tests cover empty, singleton, and multiple records.
- **4:** Storage tests use an isolated fake and cover round trip, missing key, malformed JSON, and parsed-but-invalid records.
- **2:** At least 12 tests are deterministic, independent of order, and fail with useful diagnostics when a relevant defect is introduced.

The examiner should inspect assertions and fixtures. Test count alone earns no points.

### D. Browser safety, semantics, and accessibility — 12 points

- **4:** User-controlled strings travel only to text-safe display operations; inspection and hostile-input exercise show no executable-markup sink.
- **3:** Labels, native controls, submit behavior, error association/announcement, focus behavior, and remove controls support keyboard use.
- **3:** The page remains readable and operable at 360 CSS pixels without essential horizontal clipping.
- **2:** Semantic structure and visible empty/recovery states make the application understandable without relying only on color.

### E. Engineering documentation and verification — 8 points

- **3:** README gives exact local run and test commands that work in the examiner's clean run.
- **2:** Architecture note accurately explains contracts, dependency direction, storage key, and error handling.
- **2:** All seven manual checks have concrete, plausible observation records clearly labeled as manual rather than automated evidence.
- **1:** Scope remains bounded; tradeoffs and any known limitations are stated plainly.

### F. Comprehension — 15 points

Score each response against the indicators below and require citations to the learner's actual files, functions, or tests.

1. **Boundaries and dependency direction (3):** Full credit identifies the domain model as independent, treats storage and DOM as side-effect boundaries coordinated by the controller, and explains a concrete containment benefit. A diagram must agree with the code.
2. **State invariants and atomic failure (3):** Full credit includes unique non-empty IDs, valid normalized names, positive safe-integer `n`, finite nonnegative time, and no caller-visible mutation. The trace must show validation/duplicate failure before commit and therefore no render or save of partial state.
3. **Untrusted display data (3):** Full credit traces input, normalized domain value, JSON persistence, reload validation, and DOM display. It distinguishes inert JSON/string storage from a dangerous HTML-parsing sink and cites inspection or a hostile-input test/manual observation demonstrating literal display.
4. **Persistence recovery (2):** Full credit distinguishes missing data as a normal empty success from malformed JSON and structurally invalid parsed data as recovery errors. It notes that initial recovery must preserve the original stored value until an explicit successful user mutation or recovery action.
5. **Determinism and diagnostics (2):** Full credit names two genuinely failure-prone tests and relates fixed IDs, total ordering, fresh fixtures, isolated fake storage, and independence from time/randomness/order to reproducible failures.
6. **Controlled change (2):** Full credit proposes a pure model update transition that reuses validation, preserves the target ID and uniqueness, returns a new collection or explicit failure, and leaves storage/DOM as adapters. It identifies stable validation, ordering, summary, and unrelated transition tests plus new edit cases.

Responses that merely paraphrase the prompt without submission-specific evidence receive at most half credit for that response. Technically sound designs different from the reference indicators receive full credit when the implementation supports them and the required behavior is preserved.

## Decision rule and caps

- `KICKOFF_UNIT_COMPLETED`: all critical gates pass, total score is at least 75/100, section C is at least 12/22, and section F is at least 8/15.
- `NOT_YET_COMPLETE`: any other result.

Apply these diagnostic caps before the decision rule:

- Application cannot load or core add/remove flow cannot be exercised: maximum 49.
- Automated tests do not execute, or contain fewer than six substantive assertions: maximum 59.
- Domain logic is inseparable from browser globals and cannot be tested outside the browser: maximum 69.
- Comprehension response is missing: section F is zero; no additional total-score cap.

## Examiner record

Record the submission identity, immutable artifact reference if available, executed command and exit status, browser used, observed failures, points by section, gate outcomes, cap applied, final score, and final decision. Do not modify learner files while evaluating.

---

**Provenance and status:** Examiner-only rubric independently authored for the manager-created kickoff. It is not Stanford material and was not derived from retrieved Stanford pages. Validation label: assessment specification awaiting independent application.
