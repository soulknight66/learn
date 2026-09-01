# Study Task: Stable Matching as an Executable Contract

**Artifact status:** `PREPARED_NOT_VALIDATED`  
**Unit:** `kickoff_01_stable_matching_engineering`  
**Timebox:** 8 hours. If unfinished at the timebox, submit a runnable partial attempt and document the gap honestly.

## Assignment

Build a small, reusable implementation of **left-proposing deferred acceptance** for the model in `COURSE_BRIEF.md`. Treat the mathematical preconditions as an API boundary, make invalid behavior explicit, and supply evidence that the valid outputs are stable.

Use a mainstream language available in your environment. Third-party dependencies are optional, but your run instructions must make every dependency and installation step explicit. Do not require network access during the documented test run.

## Required interface behavior

Expose one documented public operation equivalent to:

```text
stable_match(left_preferences, right_preferences) -> mapping from left IDs to right IDs
```

Both inputs are maps from participant IDs to ordered sequences of opposite-side IDs, from most to least preferred. Your concrete syntax may follow your language's conventions. State it precisely in the README.

For this unit, a valid input has all of these properties:

- the two groups are disjoint and have the same size;
- participant IDs are unique within their group and valid map keys;
- every ranking contains every opposite-side participant exactly once;
- rankings are strict and complete; and
- the empty instance is valid.

The operation must:

- return a bijection represented from left IDs to right IDs;
- return an empty mapping for the empty instance;
- use the left side as the proposing side;
- return the same observable result for repeated calls with equal inputs;
- avoid mutating caller-owned maps or ranking sequences; and
- reject every malformed instance before presenting a result as a matching.

Choose a single documented error category or result form for contract violations. Error messages must distinguish at least these fault classes: unequal group sizes, overlapping group IDs, a missing or unknown ranked participant, and a duplicate in a ranking. Do not silently repair an invalid instance.

Iteration order in a hash map is not a sufficient reproducibility contract. Explain why your result is deterministic under your implementation's scheduling choices, and add a test that would catch accidental dependence on insertion order where your language permits it.

## Required submission

Submit a compact repository containing:

```text
README.md
DESIGN.md
COMPREHENSION_RESPONSES.md
src/              # or the conventional source directory for your language
tests/            # automated tests
```

Equivalent conventional layouts are acceptable when the README maps each required item to its location.

### `README.md`

Include:

- language and runtime/tool versions;
- the exact command to run all tests from the repository root;
- dependency/setup steps that work without fetching anything during the test run;
- a concise public API description with one original input/output example; and
- current limitations and any incomplete requirement.

### Implementation

Keep input validation visibly separate from the matching state transitions. Use names that reveal the model roles. Avoid global mutable state. Internal assertions are welcome, but they do not replace boundary validation.

The valid-input matching phase must have (O(n^2)) worst-case time after rankings have been indexed, where (n) is the size of either group. Include validation and preprocessing when reporting total complexity. Do not justify complexity with wall-clock timing alone.

### `DESIGN.md`

Document:

1. the concrete input and output contract, including failure behavior;
2. the mutable state used during deferred acceptance and at least three invariants maintained across iterations;
3. a termination argument with a finite progress measure;
4. a stability argument connected to your actual state transitions;
5. what left-proposer optimality means here and why scheduling among currently free proposers does or does not change the returned partner mapping;
6. worst-case time and auxiliary-space analysis for validation, preprocessing, matching, and the test oracle separately;
7. how the stability oracle is independent of the construction logic; and
8. one production concern deliberately excluded by this unit and the contract change it would force.

If your implementation departs from your design, update the document. The code and design must describe the same system.

### Automated tests

Provide deterministic tests for all of the following:

- empty and one-pair instances;
- at least two nontrivial hand-written instances, including one in which some proposal is rejected;
- output cardinality, membership, and bijection properties;
- absence of a blocking pair, checked by a direct definition-based oracle;
- every malformed-input class named in the contract;
- non-mutation of both input maps and their ranking sequences;
- repeatability and insertion-order independence, where representable;
- all strict complete preference profiles for the (2 \times 2) case; and
- a reproducible generated suite for several larger sizes using an explicit fixed seed.

For generated cases, report enough context on failure to recreate the exact instance. The oracle must inspect the returned mapping and preferences directly; it may share parsing helpers, but it must not call the matching routine or reuse its proposal/engagement state.

### `COMPREHENSION_RESPONSES.md`

Answer every prompt in `COMPREHENSION.md`. Refer to concrete functions, tests, or sections of your design where requested. Keep claims falsifiable: identify the state or evidence that would disprove them.

## Final self-check

Before submission, start from a clean copy of your work and verify that:

- the documented test command runs without interactive input or network access;
- no generated cache, credential, machine-specific absolute path, or unrelated artifact is required;
- failures produce nonzero status through the normal test command;
- all citations and reused code are attributed with their license where applicable; and
- your README clearly labels partial or failing work instead of claiming completion.

Passing this unit, if later recorded by an independent validator, applies only to this kickoff. File presence and self-reported success are not completion evidence.

---

**Provenance:** Course-manager-authored from the stable-matching correspondence in the supplied CSDIY catalog snapshot at commit `adce8e13789dc16aa6d1fbe163e9541736defae4`. It is not an official UC Berkeley assignment. No website, repository, textbook, or official assignment content was retrieved.
