# Examiner Rubric — Collision-Risk Kickoff Unit

This rubric is independent examiner material. Do not copy it, its scoring thresholds, or its answer guidance into learner-visible locations.

## Scope and evidence rules

Score only `kickoff_probability_collision_lab_v1`. A passing result is evidence for this unit alone and never for completion of UCB CS126, its official homework, or its labs. Evaluate repository artifacts, captured commands, and reproducible behavior; a learner's prose claim that something works is not evidence.

Before scoring, apply these gates:

- Required submission files are present and learner-authored.
- The implementation and tests run without network access or undisclosed external data.
- No answer key, hidden grader, sealed reference, credential, or other learner's work appears in the submission.
- The recorded test result is not fabricated, and the JSON experiment records parse.
- Inputs used for the required experiments are within the stated model.

A safety breach, fabricated evidence, or non-running submission is `NEEDS_REWORK` regardless of points. Otherwise score out of 100; `SUCCEEDED` requires at least 75 points, at least half credit in each of sections A–E, and no gate failure. Only the harness-controlled validator may apply that state.

## A. Probability model and exact computation — 20 points

- **5:** Explicit finite model: iid uniform draws with replacement into `m` buckets; the collision event is defined unambiguously.
- **7:** Correct derivation. For `0 <= n <= m`, no-collision probability is the falling-factorial ratio `(m)_n / m^n`, equivalently the product over `i = 0, ..., n-1` of `(1 - i/m)`; collision probability is its complement.
- **4:** Correct boundaries: probability zero for `n <= 1` when `m >= 1`, and one for `n > m`; invalid bucket/draw domains are rejected consistently.
- **4:** Numerically responsible calculation, such as accumulating `log1p(-i/m)` and using `-expm1(log_no_collision)`, or a comparably justified method. Large factorials converted to float and unexplained naive subtraction do not earn these points.

## B. Simulation and statistical reasoning — 20 points

- **5:** Each trial samples the specified model and detects any duplicate correctly; estimate equals `collision_count / trials`.
- **5:** The averaged indicator is identified as Bernoulli with mean `p` and variance `p(1-p)`; the sample-mean variance is distinguished from single-trial variance.
- **5:** A defensible 95% binomial-proportion interval is implemented and named. Wilson score is expected for a strong solution; a carefully handled exact interval or justified alternative is acceptable. A bare unbounded normal interval loses credit, especially at extreme counts.
- **5:** The required matrix is run with a recorded seed and adequate trial count. Interpretation treats interval coverage as probabilistic evidence, not a deterministic correctness oracle.

## C. Software design and data contract — 20 points

- **5:** Exact model, trial generation, aggregate simulation, CLI, and serialization have clear boundaries and documented interfaces.
- **4:** Randomness is injected or locally constructed; normal behavior does not consume or reseed module-global random state.
- **4:** Domain errors are clear and consistent; CLI errors return nonzero and do not leave a success-looking output.
- **4:** JSON conforms to the specified field names and types; counts and probabilities satisfy invariants; schema, interval method, parameters, and seed are retained.
- **3:** Output is safely committed (for example, write and flush a sibling temporary file followed by `os.replace`) with cleanup behavior explained. Merely opening the destination in write mode is insufficient.

## D. Deterministic verification — 20 points

- **5:** `unittest` command works offline from a clean checkout and has bounded normal runtime.
- **5:** Boundary and invalid-input cases cover zero/one draw, `n > m`, invalid buckets/draws/trials, and probability/count ranges.
- **4:** Same-seed repeatability is demonstrated, and a test shows isolation from global RNG state.
- **3:** An independently expressed small-input oracle agrees with the production exact method. Reusing the same helper or formula implementation on both sides is not independent evidence.
- **3:** JSON and CLI success/failure paths are exercised deterministically. Any statistical test uses fixed inputs and documents a deliberately controlled false-failure risk.

## E. Analysis and reproducibility — 15 points

- **4:** Report contains model, derivation, numerical method, estimator, and interval assumptions in the learner's own reasoning.
- **4:** Complete required-matrix results are traceable to parameters, seed, trial count, code/test instructions, and versioned records; cherry-picking is not evident.
- **4:** Conclusions separate model error, implementation error, floating-point effects, and sampling variability. At least one genuine limitation is named.
- **3:** README lets an examiner reproduce tests and one experiment without guessing, and proposes a proportionate next engineering step.

## F. Comprehension — 5 points

Award 0.5 point per question when the response is substantively correct and tied to the learner's design where applicable.

1. Must state iid uniform sampling with replacement and define sequences (or an equivalent finite outcome space).
2. Must use the complement/no-collision derivation and handle the pigeonhole boundary.
3. Expected issues include factorial overflow/conversion, product underflow, cancellation near zero, and accumulated roundoff; mitigation must match code.
4. Must identify Bernoulli indicators, expectation `p`, variance `p(1-p)`, sample-mean variance `p(1-p)/T`, and justify interval construction.
5. Beyond seed, accept parameters, PRNG/algorithm behavior, code/runtime version, trial count, model/schema version, and environment as relevant facts.
6. Must separate invariant/replay tests from repeated-sampling claims and avoid unseeded pass/fail behavior.
7. Must recognize expected noncoverage, avoid declaring either correctness or a bug from one miss, and propose replay, exact/oracle, seed, count, model, and repeated-coverage checks.
8. Must address a distribution/model abstraction, richer provenance, tests with controlled skew/correlation, and a record that identifies the new model.
9. Must mention dependency control plus isolation; concurrency races or test-order coupling from global state are valid consequences.
10. Must identify truncation/partial JSON risk and describe the visibility guarantee and limitations of temporary-write plus atomic replacement (or an equivalent strategy).

## Validation record

The examiner should preserve: validation label, test argv, exit status, bounded-runtime result, captured logs, reviewed artifact paths, score by section, gate findings, and final validator decision. If validation fails, retain that evidence for a later attempt rather than rewriting history.
