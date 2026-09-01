# Independent evaluation rubric: reproducible k-NN kickoff

This rubric evaluates only the bounded manager-authored kickoff unit. It must not be used to assert completion of CS189 or equivalence to an official UC Berkeley assignment.

## Evaluation procedure

Evaluate observable artifacts, not learner claims. Work from a clean copy, inspect the required paths, and run:

```bash
PYTHONPATH=submission/src python3 -m unittest discover -s submission/tests -v
python3 submission/src/experiment.py --seed 189 --output /tmp/knn-run-a.json
python3 submission/src/experiment.py --seed 189 --output /tmp/knn-run-b.json
cmp /tmp/knn-run-a.json /tmp/knn-run-b.json
```

Use a harness-controlled temporary directory instead of `/tmp` where isolation policy requires it. Add independent black-box tests; do not rely only on learner-authored tests. Do not grant credit for inaccessible, network-dependent, or manually described behavior.

## Mandatory gates and score caps

- Missing required paths or an implementation that cannot be imported and exercised: maximum **35**.
- Missing or nonfunctional experiment/JSON artifact: maximum **60**.
- Missing or undiscoverable learner test suite: maximum **65**.
- Test data influencing preprocessing, `k` selection, or selection tie-breaking: maximum **74**.
- Nondeterministic specified ties or non-byte-stable default artifacts: maximum **74**.
- Any dependency on a network resource or undeclared third-party package: maximum **74**.
- Unauthorized solutions, hidden tests, secrets, sealed references, or another learner's work invalidate the evidence; stop and report through the harness rather than exposing the material.

A passing result requires at least **75/100**, all mandatory gates, and independent execution by the worker harness.

## Scored criteria

### A. Classifier correctness — 25 points

- **5:** validates `k`, nonempty rectangular finite numeric fit data, nonempty string labels, lengths, fitted state, and query dimension/type exactly as specified.
- **5:** computes population means/scales from fit data only, handles zero variance with scale 1, exposes tuples, and applies the same transform to stored training rows and queries.
- **6:** squared-distance calculation and neighbor ordering by distance then original training index are correct.
- **5:** vote resolution correctly applies count, per-label selected-neighbor distance sum, then lexicographic label.
- **4:** `fit`/`predict` return types, empty-query behavior, exception classes, and repeated-fit behavior are coherent and conforming.

### B. Experiment methodology — 20 points

- **5:** generator call order, local RNG use, stratified shuffles, slice boundaries, final partition shuffles, and 144/48/48 counts match the task.
- **6:** each candidate is fit on training only; validation selects `k`; ties choose smaller `k`; test data remains untouched until final evaluation.
- **5:** final model is freshly fit on combined training and validation data, then evaluated once with correct accuracy and actual-by-predicted confusion-matrix orientation.
- **4:** CLI parsing, nonzero invalid-argument behavior, output-parent handling, and default behavior are correct.

### C. Software-engineering quality — 20 points

- **5:** model, experiment orchestration, serialization, and CLI concerns are separated into testable functions with clear invariants.
- **4:** fit owns its state; caller inputs are not mutated; later caller mutation cannot change predictions; no module-global mutable RNG/model state leaks between runs.
- **4:** edge failures are deliberate and consistent, with no silent truncation, implicit ragged arrays, NaN/Infinity propagation, or Boolean-as-number acceptance.
- **4:** deterministic ordering and serialization avoid timestamps, absolute paths, hash-order dependence, and other run-specific data.
- **3:** implementation is readable, reasonably factored, and free of dead or gratuitously complex code.

### D. Tests — 20 points

- **7:** independent assertions cover distance ranking, training-index ties, all three voting stages, and prediction of multiple/empty queries.
- **5:** assertions cover zero variance, fitted statistics, invalid inputs, pre-fit prediction, copying, and non-mutation.
- **5:** experiment tests cover exact deterministic splits, disjoint row identity, selection ties, metric orientation, and byte equality across runs.
- **3:** tests are deterministic, isolated in temporary directories, discoverable by the required command, and fail for a plausible defective implementation rather than merely exercising lines.

### E. Evidence and documentation — 10 points

- **6:** `experiment.json` parses, contains all required provenance/configuration/count/selection/test fields, agrees with an independent recomputation, and is canonicalized as requested.
- **4:** README commands work and its design, leakage boundary, complexity, deterministic rules, limitations, and risks agree with the code.

### F. Comprehension — 5 points

Award credit across all eight responses for correct, implementation-connected reasoning. Look for these ideas without requiring identical wording:

- square root is strictly increasing on nonnegative values, so omitting it preserves rank while not preserving reported distance magnitude;
- deterministic distance/index and vote ordering resolves otherwise implementation-dependent choices, although original row index deliberately makes input order observable in some ties;
- unlabeled aggregate statistics can still leak test-distribution information, and every transform used during selection must be fit only on the corresponding training data;
- reproducibility and predictive correctness are separate properties requiring separate assertions;
- a full-sort implementation is typically dominated by per-query distance computation plus ordering, and an alternative such as a heap, k-d tree, or ball tree has dimensional/data tradeoffs;
- validation supports model choice while the held-out test estimates the already-fixed procedure; deterministic selection removes ambiguity;
- reproducibility needs generator identity/parameters, seed, split and model rules, while real data additionally needs stable identity, version/hash, access/license basis, and retrieval provenance.

## Completion record

Report the numeric score, each applied cap, command results, and paths or captured logs supporting the decision. A passing score is evidence only for `kickoff_01_reproducible_knn`; the course remains incomplete and eligible for later, separately validated expansion.
