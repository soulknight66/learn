# Independent rubric: Trustworthy Convex Allocation Solver

Examiner-only material. Do not copy this rubric, its reference results, or its evaluation cases into a student-safe view.

## Authority and scope

Evaluate the submitted kickoff independently. Learner prose and learner-run tests are claims to inspect, not proof of correctness. Run fresh cases in an isolated copy using only the documented Python environment. A score is evidence for a harness-controlled validator; the examiner must not mark the whole course complete.

Passing this unit requires **80/100 or more and every gate below**.

## Mandatory gates

- The documented `unittest` suite and CLI run offline with the Python standard library only.
- Fresh well-scaled valid examiner cases produce finite diagnostics and correct objective values; comparison with a high-accuracy reference uses the condition-aware allowance defined below rather than confusing residual tolerance with coordinate error.
- No `CONVERGED` result violates nonnegativity or the budget equality beyond the input tolerance; an honest `MAX_ITERATIONS` result is judged by its status and recomputed diagnostics rather than this convergence gate.
- `MAX_ITERATIONS` is never represented as `CONVERGED`; invalid data is never silently repaired into a successful result.
- Repeated execution on identical input bytes produces byte-identical standard output and the correct raw-input SHA-256.
- The submission does not claim official Stanford authorship, retrieval of absent materials, independent validation, job success, or whole-course completion.

Failure of any gate means the unit is not promotable even if the point total reaches 80.

## Reference mathematics

For valid input, the feasible set is the nonempty compact simplex \(C=\{x:x\ge0,\mathbf{1}^Tx=B\}\). It is convex. The Hessian of the objective is \(\operatorname{diag}(a_1,\ldots,a_n)\), which is positive definite because every \(a_i>0\). Thus the objective is strictly convex and has exactly one minimizer on \(C\).

The gradient is \(\nabla_i f(x)=a_i(x_i-d_i)\), and its Euclidean Lipschitz constant is \(L=\max_i a_i\). The specified threshold construction is the Euclidean projection onto \(C\). At an optimum, the projected-gradient fixed-point residual is zero. A common positive rescaling of every weight changes objective scale but not the unique optimizer, and a permutation of item records permutes the associated allocations.

The fixed activation charge is discontinuous at zero and is not convex. The convexity, uniqueness, and projected-gradient optimality guarantees from the base model therefore cannot simply be carried over.

## Fresh examiner cases

Do not rely only on these cases; add at least two independently chosen valid cases and malformed inputs for every validation family.

1. **Zero budget:** for any valid items, the unique allocation is all zeros.
2. **One item:** its allocation is exactly the entire budget.
3. **Boundary clipping:** with weights \((1,1)\), targets \((2,-1)\), and budget \(1\), the optimizer is \((1,0)\) and the objective is \(1\).
4. **Three active items:** with weights \((1,2,4)\), targets \((0.8,0.4,0.3)\), and budget \(1\), the optimizer is approximately \((0.5142857143,0.2571428571,0.2285714286)\) and the objective is \(1/14\).
5. **Metamorphic checks:** permute case 4 and match by ID; separately multiply all its weights by 7.5. Allocation must be unchanged within tolerance, while the scaled case's objective is multiplied by 7.5.
6. **Exhaustion:** choose a tolerance/iteration combination that forces the documented limit and confirm exit 3, `MAX_ITERATIONS`, and the required non-independent validation label.

Recompute objective and residuals independently from parsed output. Check the raw input hash from bytes, not from reserialized JSON.

For a converged result with \(n\) items and condition ratio \(\kappa=\max_i a_i/\min_i a_i\), compare each allocation coordinate with a high-accuracy independent reference using

\[
\max\!\left(10^{-8},\ 2\sqrt{n}\,\kappa\,\texttt{tolerance}\right).
\]

The factor accounts conservatively for converting the specified infinity-norm fixed-point residual into a coordinate-error check for this strongly convex projected-gradient map. Also recompute and enforce the submitted fixed-point and feasibility residual conditions directly. Do not accept a large error merely because the comparison allowance is large; inspect objective, feasibility, and an independently solved reference together.

## Scoring

### 1. Mathematical model and reasoning — 20 points

- 5: `DESIGN.md` states the exact objective, feasible set, and preconditions without changing their meaning.
- 5: Convexity of the feasible set is justified correctly.
- 5: Positive definiteness, existence, and uniqueness are connected correctly, without claiming that convexity alone always implies uniqueness.
- 5: The activation-charge analysis correctly identifies nonconvexity and withdrawn guarantees.

### 2. Projection and solver correctness — 30 points

- 10: Simplex projection is correct for zero budget, interior cases, clipping, ties, and original-order restoration.
- 8: The gradient step, initialization, iteration limit, and state updates implement the specified algorithm.
- 8: Fresh cases match independently recomputed allocations within the condition-aware allowance, and objectives and reported residuals pass independent recomputation.
- 4: Fixed-point and feasibility residuals are computed consistently, and exhaustion cannot be mislabeled.

### 3. Validation and failure contract — 15 points

- 8: All numeric, structural, identity, range, boolean, NaN, and infinity cases in the task are rejected deterministically.
- 4: Exit codes, output streams, statuses, and error objects match the interface contract with no partial-success output.
- 3: Extreme but valid values fail honestly if numerical limits prevent a reliable result.

### 4. Tests and independent evidence — 15 points

- 5: Projection, solver boundaries, invalid input, and exhaustion have focused deterministic unit tests.
- 4: CLI byte determinism and hashing are tested at the process boundary.
- 3: Permutation and common-weight-rescaling properties are tested correctly.
- 3: The grid oracle is independent of the production solver, and its finite resolution is not presented as a proof.

### 5. Software design, determinism, and provenance — 15 points

- 4: Model, projection, solver, and CLI responsibilities are separated; the core is free of file I/O and process exits.
- 3: Output ordering and serialization are stable and contain no time-, path-, or randomness-dependent fields.
- 4: Course/unit IDs, raw-input SHA-256, algorithm version, and the non-independent validation label are accurate.
- 4: `README.md`, `DESIGN.md`, and `VALIDATION.md` give reproducible commands and honestly report limitations and observed evidence.

### 6. Comprehension responses — 5 points

Award 0.5 point per prompt for a direct, technically correct response tied to the learner's implementation. Do not award credit for copied definitions that do not answer the question.

## Promotion record

Record the raw score, each gate result, commands executed, environment, fresh input hashes, observed output hashes, and any discrepancies. Label the result `INDEPENDENTLY_EVALUATED` only after actually performing these checks. Forward evidence to the worker-harness-controlled validator. A promoted result completes only `unit_kickoff_trustworthy_convex_allocation_v1`; course status remains incomplete.

---

Rubric provenance: independently authored by the course manager for this bounded kickoff from the supplied catalog snapshot; no linked course content or official assignment was retrieved.
