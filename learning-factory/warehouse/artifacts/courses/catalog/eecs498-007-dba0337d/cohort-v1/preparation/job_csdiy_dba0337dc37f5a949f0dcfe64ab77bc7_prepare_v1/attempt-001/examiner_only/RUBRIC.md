# Independent examiner rubric: deterministic image k-NN kickoff

## Handling and decision boundary

This file is examiner-only. Do not copy its scoring guidance, oracle cases, or expected comprehension content into a learner-safe path.

Evaluate only `kickoff_unit_01_deterministic_image_knn`. A passing result is evidence for this bounded unit, not for the whole course. The examiner records observations and scores; only the worker-harness-controlled validator may promote the unit to `SUCCEEDED`.

Run the submission in a clean process from the workspace root with `PYTHONPATH=submission`. Do not trust prose claims or learner-recorded output as proof: rerun tests and independent probes. Do not use a network, install packages, or supply unavailable catalog materials.

## Preconditions and caps

The submission is eligible for full assessment only if the expected package imports without side effects and the documented test discovery command starts successfully.

- If `KNNClassifier` cannot be imported or no successful `fit`/`predict` call is possible, the result cannot pass and the total is capped at 35.
- If the CLI cannot process any valid request, the total is capped at 70.
- If learner-authored tests are absent or cannot be discovered, the total is capped at 70.
- If correctness depends on network access, undeclared third-party packages, nondeterministic external state, or restricted material, the result cannot pass.
- Missing comprehension responses cap the total at 84; responses that merely restate prompts receive no comprehension credit.

A numerical score of at least 80/100, at least 30/40 in model correctness, and no non-pass condition above is the recommended validation threshold. Crossing the threshold does not itself change job state.

## Scoring

### 1. Model contract and correctness — 40 points

- **Construction and lifecycle (5):** rejects non-integer, Boolean, and nonpositive `k`; prediction before fit fails clearly; `fit` returns `self`.
- **Input invariants (8):** validates nonempty rectangular training features of positive dimension, finite real non-Boolean values, matching nonempty string labels, query dimensions, and oversized `k`. Empty query batches return `[]`.
- **Defensive ownership (5):** fitted state is isolated from nested mutation of caller training data; prediction does not mutate query data; callers cannot alter later behavior by mutating a returned prediction list.
- **Distance and ranking (8):** computes squared Euclidean distance correctly and ranks by distance then original training index.
- **Voting (10):** maximizes vote count, then minimizes the selected neighbors' aggregate distance for tied labels, then selects the lexically smallest tied label.
- **Batch behavior (4):** returns exactly one string per query, preserves query order, and handles repeated calls consistently.

Award no credit for a behavior that appears only in hard-coded fixtures. Minor exception-message wording differences are acceptable; exception type use must be deliberate and consistent.

### 2. Command-line behavior and reproducibility — 12 points

- Parses the specified UTF-8 JSON shape and invokes the same model behavior as the API (4).
- On success, emits only one sorted-key JSON object with `k` and ordered predictions plus exactly one trailing newline (3).
- Repeated clean-process runs are byte-identical (2).
- Malformed JSON, missing fields, invalid model data, and unreadable input fail nonzero with a concise stderr diagnostic and no success JSON on stdout (3).

### 3. Learner verification — 16 points

- Tests run with the exact discovery command and require neither network nor order dependence (3).
- Normal prediction and the two stages of voting tie resolution are asserted with hand-checkable fixtures (4).
- Lifecycle, `k` boundaries, ragged/dimension errors, nonnumeric/Boolean/non-finite values, and label errors are covered (4).
- Nested-input non-mutation and returned-result isolation are demonstrated (2).
- The CLI is exercised as a subprocess, including byte-for-byte repeatability and at least one failure (3).

Tests earn credit for observable contracts, not assertions about private fields or copied production logic that can reproduce the same bug.

### 4. Software-engineering quality — 16 points

- Model logic, CLI adaptation, and validation responsibilities are cohesive and reasonably separated (4).
- Public API and exception behavior are documented; names and types make invariants understandable (3).
- No import-time execution, global mutable learned state, irrelevant generated files, or swallowed exceptions (3).
- `README.md` gives exact clean-run commands and the examiner can reproduce the described workflow (3).
- `ENGINEERING_NOTE.md` accurately describes boundaries, invariants, determinism, testing strategy, limitation, and replacement path within the requested scope (3).

Prefer simple standard-library code. Do not reward abstraction volume by itself.

### 5. Comprehension — 16 points

Score each response for a correct claim, reasoning tied to the implementation, and an explicit tradeoff. Expected substance:

1. **Complexity (3):** copying during fit takes linear work and stored space in `n*d`. Each brute-force query computes `n` distances in `Theta(n*d)`; full sorting adds `Theta(n log n)`, while a valid bounded-selection design can use `Theta(n log k)`. The answer must multiply query work by `q` and distinguish persistent from temporary space.
2. **Determinism (3):** original index orders equal distances at the cutoff, aggregate distance resolves an equal vote count, and lexical order makes the final choice total. Iterating an unordered container, changing stable-sort inputs, parallel collection, or replacing the tie key are valid refactor risks when explained precisely.
3. **Ownership (2):** retaining nested caller lists permits post-fit mutation to alter dimensions, distances, labels, or predictions without another fit. Copying buys state integrity at `Theta(n*d)` time and memory cost.
4. **Evaluation leakage (3):** choosing `k` on reported test examples optimizes to the test set and biases the estimate. Training fits stored examples, validation selects `k`, and a previously untouched test set is evaluated once after choices are frozen.
5. **Vision boundary (3):** flattening ignores locality and makes spatial rearrangements look like arbitrary vector changes. A credible response preserves the classifier-facing `fit`/`predict` contract or introduces a clearly described model protocol while replacing the model behind it.
6. **Scaling (2):** accepts an exact index, partial selection, vectorized backend, or approximate-neighbor strategy if the learner states latency/memory effects and whether exact ranking can change. Input, ordering, output, error, and reproducibility tests should remain unless an intentionally revised approximation contract is versioned and tested.

## Independent oracle probes

Use fresh mutable lists for every probe. These expected results are examiner evidence and must not be placed in learner-safe files.

1. Ordinary nearest neighbor: train `[[0, 0], [0, 2], [4, 4]]` with labels `["dark", "edge", "light"]`, `k=1`; query `[[0.1, 0.2], [3.9, 4.1]]` must yield `["dark", "light"]`.
2. Equal-distance cutoff: train `[[-1, 0], [1, 0], [0, 3]]` with labels `["left", "right", "far"]`, `k=1`; query `[[0, 0]]` must yield `["left"]` because the original index breaks the distance tie.
3. Aggregate-distance vote tie: train `[[1], [3], [2], [-2]]` with labels `["A", "A", "B", "B"]`, `k=4`; query `[[0]]` must yield `["B"]` because both labels receive two votes but B's aggregate selected-neighbor distance is smaller.
4. Lexical vote tie: train `[[1], [-1]]` with labels `["zebra", "alpha"]`, `k=2`; query `[[0]]` must yield `["alpha"]`.
5. Isolation: fit on nested mutable feature and label lists, record a prediction, mutate inner rows and labels drastically, and confirm the fitted model gives the original prediction. Mutating a returned predictions list must not affect the next call.
6. Invalid values: independently probe `True`, `False`, strings, `NaN`, positive and negative infinity, ragged rows, zero-dimensional rows, a label-count mismatch, an empty label, a query dimension mismatch, and `k > n`.
7. CLI: run the same valid request twice in separate processes and compare raw stdout bytes; then verify invalid JSON and invalid model data both fail as contracted.

## Examiner record

Record the exact revision assessed, command lines, exit codes, score by section, failed oracle probes, and paths to captured logs. Preserve failed-attempt evidence. The final validation label must be explicit and scoped to the kickoff unit.
