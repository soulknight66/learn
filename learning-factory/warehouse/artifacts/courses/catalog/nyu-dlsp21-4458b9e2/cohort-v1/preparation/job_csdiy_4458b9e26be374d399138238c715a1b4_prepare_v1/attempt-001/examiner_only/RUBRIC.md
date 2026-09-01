# Independent rubric — engineered softmax kickoff

Examiner-only status: **MANAGER-AUTHORED ASSESSMENT CONTROL — DO NOT PLACE IN THE LEARNER VIEW**  
Validation label: **RUBRIC_PREPARED_NOT_APPLIED**

## Scope and evidence rule

This rubric evaluates only unit `managed_unit_01_engineered_softmax` for course `course_4458b9e26be374d399138238c715a1b4`. It does not evaluate or certify the NYU DLSP21 course, any official lecture, or any official assignment.

Score the files and behavior present in the isolated learner attempt. Re-run commands and construct independent probes; do not accept README statements, self-reported metrics, or a worker's prose as proof. Do not retrieve external course material for this evaluation. Preserve command output and the submitted metrics file as validation evidence.

## Examiner procedure

1. Inventory the attempt and confirm that no examiner file, credential, downloaded course archive, environment, or unrelated learner file is present.
2. From the attempt root, run `PYTHONPATH=src python3 -m unittest discover -s tests -v` with the harness timeout and captured logs.
3. Run the configured CLI twice in separate harness-owned temporary directories. Compare output bytes and retain their SHA-256 digests.
4. Import the public functions into an independent probe. Exercise extreme logits, malformed shapes, non-finite values, non-mutation, and selected finite-difference coordinates that are not copied from learner tests.
5. Parse the submitted and regenerated JSON; verify types, finiteness, configuration, dataset digest, outcome checks, and validation label.
6. Read `DESIGN.md`, `README.md`, and `artifacts/comprehension.md`, checking explanations against observed behavior.

Use argv-based subprocess execution, a bounded timeout, a new process group, and captured logs. Harness scratch output may be removed explicitly after evidence is recorded; preserve the learner attempt and any failure evidence.

## Mandatory gates

All gates must pass for unit completion, regardless of point total:

- the required test command runs and all discovered tests pass;
- only the Python standard library is needed at runtime and for tests;
- independent probes confirm finite extreme-logit behavior and input rejection;
- an independent centered finite-difference probe agrees with selected analytic weight and bias gradients within a justified tolerance;
- the configured training run reduces loss and reaches at least `0.90` fixture training accuracy;
- same-argument isolated runs emit byte-identical valid metrics;
- the learner provides substantive original answers to all eight comprehension prompts; and
- no learner-facing file contains this rubric, an examiner answer key, hidden test content, secrets, or another learner's work.

A non-runnable submission, missing numerical core, or fabricated metrics receives at most 49 points. A missing design note, metrics artifact, or comprehension response receives at most 79 points. Record the reason for every cap.

## Scored criteria (100 points)

### A. Public contracts and implementation structure — 12 points

- **5:** required public signatures are importable; returned shapes and mean-loss semantics match the prompt.
- **4:** explicit checks consistently reject empty, ragged, mismatched, non-finite, and out-of-range inputs with `ValueError` near the public boundary.
- **3:** functions do not mutate caller data; responsibilities are separated cleanly enough for independent testing.

### B. Numerical correctness and stability — 20 points

- **6:** softmax uses maximum shifting, returns a probability per logit, and satisfies bounds and normalization within a stated tolerance.
- **6:** cross-entropy is computed from logits with stable log-sum-exp rather than `log(softmax(...)[label])`.
- **5:** independent ordinary and extreme cases agree with separately computed reference values and remain finite for finite tested inputs.
- **3:** limitations and approximate-comparison choices are accurate and documented.

Do not award the relevant item when expected values are produced by calling the learner function being assessed.

### C. Analytic gradient and training behavior — 20 points

- **10:** mean-loss weight and bias gradients are correct in shape, sign, indexing, and averaging on independent probes.
- **6:** a centered finite-difference check with a sensible step confirms several weight entries and at least one bias entry, including a nonzero coordinate.
- **4:** full-batch updates use the configured learning rate; the configured fixture run lowers loss and reaches the required training accuracy.

The reference derivative for one example is `dL/dz_c = p_c - 1[c = y]`; for a batch, average these terms, multiply by each feature for weight entries, and sum them directly for bias entries. The examiner should derive probe values independently, not import learner gradient helpers.

### D. Test quality and fault detection — 18 points

- **4:** tests cover normalization, shift invariance, a genuinely independent small expected case, and extreme finite inputs.
- **4:** negative tests cover every required malformed-input family and assert the intended `ValueError`, not any exception.
- **3:** tests demonstrate no mutation and document meaningful tolerances.
- **4:** gradient and one-step loss tests would fail under plausible sign, averaging, and indexing mutations.
- **3:** CLI tests exercise deterministic repeatability and a failing invocation that leaves no completed target.

### E. Reproducible CLI and artifact provenance — 12 points

- **4:** `argparse` validation, nonzero failure behavior, local seeded randomness, and atomic replacement work as specified.
- **5:** JSON is sorted, newline-terminated, deterministic, parseable, correctly typed, finite, and contains every required field and exact validation label.
- **3:** the dataset digest matches the canonical serialization; two isolated outputs are byte-identical and contain no ambient timestamp or path.

Compute the reference digest directly from the task fixture with `json.dumps(fixture, separators=(",", ":"), ensure_ascii=True).encode("utf-8")` and SHA-256.

### F. Software-engineering analysis — 8 points

- **2:** `README.md` gives exact working commands, supported Python version, file map, and artifact location without an inflated completion claim.
- **3:** `DESIGN.md` accurately explains contracts, exception placement, stability, gradient-check independence, and controlled nondeterminism.
- **2:** complexity states `O(NCD)` time per full-batch epoch and distinguishes `O(CD)` model/gradient storage from optional per-example or batch intermediates.
- **1:** the proposed production-hardening change addresses a concrete risk and is proportionate.

### G. Comprehension — 10 points

Award across all eight responses; partial credit requires a defensible chain of reasoning tied to the learner's implementation.

- **Q1:** proves common-shift cancellation in exact arithmetic and distinguishes overflow, underflow, rounding, and non-finite inputs.
- **Q2:** explains why a rounded probability can become zero before `log`, while stable log-sum-exp retains a finite loss for finite logits; supplies a coherent extreme case.
- **Q3:** reaches the reference logit derivative above, applies the feature multiplier, handles bias, gives matching shapes, and places the `1/N` factor consistently.
- **Q4:** derives `O(NCD)` time; accurately separates `O(CD)` persistent model and gradient storage from implementation-dependent `O(C)` or `O(NC)` intermediates.
- **Q5:** identifies controlled seed/order/serialization and ambient-input exclusions, while withholding cross-version, cross-platform, generalization, and correctness claims.
- **Q6:** contrasts local derivative agreement with end-to-end optimization behavior; valid false-agreement risks include shared formulas, unsuitable step size, loose tolerance, only zero-gradient coordinates, or checking too few coordinates.
- **Q7:** connects one concrete contract to a realistic downstream failure, defends a stable public exception boundary, and proposes a discriminating negative test.
- **Q8:** rejects training-set accuracy as a generalization or course-completion claim and proposes a minimal held-out or perturbation evaluation tied to one explicit question.

## Decision

Mark the unit `SUCCEEDED` only when the score is at least **80/100**, every mandatory gate passes, and the worker-harness-controlled validator records durable evidence. Otherwise record `FAILED` with score, failed gates, logs, and artifact locations; do not erase the attempt.

Even a `SUCCEEDED` decision means only this manager-authored kickoff unit succeeded. The course status remains partial. Later course expansion requires separately retrieved and classified resources, new unit contracts, and independent validation.

## Provenance

This rubric was authored from the supplied CSDIY catalog snapshot, not copied from NYU material. Catalog source file: `docs/深度学习/NYU-DLSP21.en.md`; commit: `adce8e13789dc16aa6d1fbe163e9541736defae4`; content SHA-256: `9be457f99f8e3da9dffc38170e0fc1c5a4186ee20f2eda2d5babc1c4181e4ec0`. External retrieval performed: **no**.
