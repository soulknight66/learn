# Independent examiner rubric: reliable browser vertical slice

This rubric evaluates only `kickoff_01_reliable_browser_vertical_slice`. It must not be used to claim completion of the wider course. Examine the submitted files and rerun checks in the worker-controlled environment; learner prose alone is not evidence.

## Preconditions and critical gates

Before scoring, record the submission identifier, environment, commands run, exit codes, and locations of captured evidence. The unit cannot pass if any of these conditions holds:

- the implementation or required notes are missing or cannot be opened;
- automated tests cannot be run from the documented command, or return a failing/nonzero result;
- the core feature cannot add, order, toggle, and reload valid items;
- invalid form input changes persisted application state;
- item titles are inserted as executable/interpreted HTML;
- the submission depends on unavailable upstream recordings or assignments; or
- comprehension responses are missing, copied, or materially inconsistent with the submitted implementation.

After gates pass, score each section using direct inspection and independently reproduced behavior. A passing unit requires at least 75/100 overall and at least half of the available points in every numbered section.

## 1. Requirements and behavior — 25 points

- **6 points:** Title, priority, and estimate constraints are enforced after appropriate parsing/trimming, with invalid additions leaving state unchanged.
- **7 points:** Ordering implements all four keys in the stated direction, including deterministic creation-sequence tie-breaking and reordering after completion changes.
- **4 points:** Add and completion flows update the UI consistently without duplicate or partially applied state.
- **4 points:** Titles containing markup-like characters render literally; examiner inspection finds no unsafe HTML insertion path for user titles.
- **4 points:** The submitted product stays inside the declared single-browser vertical-slice boundary while satisfying every required behavior.

## 2. Design and code quality — 20 points

- **8 points:** Validation, comparison, and state transitions are in a domain module that imports no DOM or browser-storage APIs and can be called directly by tests.
- **5 points:** State transitions have clear inputs/outputs and do not mutate prior state; creation sequence remains unique and monotonic for accepted states.
- **4 points:** Browser integration has understandable event, render, and persistence boundaries, with failures handled deliberately.
- **3 points:** Names, file organization, and comments make invariants and non-obvious decisions maintainable without needless abstraction.

## 3. Persistence and fault handling — 15 points

- **5 points:** One documented storage key preserves the collection and next sequence, and a valid state round-trips across reload.
- **6 points:** Restore validates container shape and every required field/type/range, including sequence consistency; malformed data is rejected as a whole rather than silently normalized.
- **4 points:** Missing or rejected storage produces an empty usable application and an appropriate non-destructive notice, without overwriting the malformed value before the learner has a chance to observe the condition.

## 4. Testing and reproducibility — 20 points

- **10 points:** Automated assertions cover all requested validation boundaries, trimming, each comparator key and a complete tie, non-mutating completion, malformed restoration, and any domain serialization round trip.
- **4 points:** Tests are deterministic, isolated from prior browser state, capable of failing the process, and include assertions strong enough to detect reversed keys or skipped tie-breakers.
- **3 points:** `ENGINEERING_NOTE.md` supplies usable run/test instructions, environment, boundaries, storage schema/key, references, and candid limitations.
- **3 points:** `VERIFICATION.md` contains the exact command/result and concrete, dated manual observations for all five requested checks; examiner reproduction is consistent with them.

## 5. Accessibility and responsive use — 10 points

- **4 points:** Native semantic controls have programmatic labels, keyboard-operable actions, logical focus behavior, and a visible focus indicator.
- **3 points:** Validation and status feedback is perceivable by assistive technology and does not depend on color alone; the relevant input is identifiable.
- **3 points:** At a narrow viewport, controls and content remain readable and operable without obscured actions or avoidable horizontal scrolling.

## 6. Comprehension — 10 points

Award credit for reasoning tied to submitted evidence, not for matching exact wording.

- **2 points:** The learner accurately explains lexicographic comparator decisions, determinism, and the creation-sequence tie-breaker.
- **2 points:** The learner correctly distinguishes pure/domain work from browser effects and traces validation and Add-flow failure boundaries.
- **2 points:** The learner explains that parsing is not validation and identifies at least four actual restore invariants plus the implemented rejection behavior.
- **2 points:** The learner proposes a comparator test that genuinely improves defect detection and explains two accessibility decisions in terms of user needs and observations.
- **2 points:** The learner distinguishes scope control and known limitations from unmet requirements, proposes a suitably small next step, and cites the reviewed submission and test command.

## Examiner record

Record section scores, total, gate results, command evidence, and a concise discrepancy list in the harness-controlled validation record. On a passing result, promote only this unit. On failure, preserve the attempt and evidence so a revision can target observed discrepancies.
