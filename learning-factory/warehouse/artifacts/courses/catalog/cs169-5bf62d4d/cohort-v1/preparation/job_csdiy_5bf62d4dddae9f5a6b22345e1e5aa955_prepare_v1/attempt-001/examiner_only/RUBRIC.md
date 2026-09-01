# Examiner-Only Rubric: Dependency-Planner Kickoff

This rubric is independent evaluation guidance. Do not copy it or its answer notes into learner-visible materials.

## Evaluation protocol

Evaluate only the submitted kickoff artifacts. Start from a clean copy, follow the learner's README literally, run the documented full test command, and make direct endpoint probes where needed. Treat executable behavior and files as evidence; do not award credit for unsupported prose claims. Do not retrieve CS169 assignments, solutions, hidden graders, or restricted material to conduct this evaluation.

Record the commands, observed results, and any environment limitation. A passing result may validate only this kickoff unit.

## Critical conditions

The unit cannot pass if any of the following holds:

- the submitted service or tests cannot be run from the documented commands because of a submission defect;
- there is no automated endpoint-level test or no automated test of cycle behavior;
- the core response can omit tasks, duplicate tasks, or violate a dependency on an accepted acyclic request;
- a cyclic request is returned as a successful usable plan;
- the evidence is only a prose assertion, is materially inconsistent with the submitted version, or exposes secrets; or
- the submission incorporates restricted assessment content or represented official-course solutions.

An examiner-caused infrastructure failure is not a learner failure: preserve the evidence and mark evaluation blocked.

## Scored criteria (100 points)

### 1. Contract and scope — 15 points

- 6: `POST /plans` and `GET /health` behavior is clear and matches the assigned status and JSON rules.
- 5: The learner-authored story and acceptance scenarios are concrete, testable, and remain within the vertical slice.
- 4: Deferred work and limitations are explicit; the submission does not claim to be an official CS169 assignment or full-course completion.

### 2. Functional behavior — 25 points

- 8: Every accepted acyclic request returns each declared task exactly once while respecting all dependencies.
- 5: Independent eligible tasks are selected with lexicographic tie-breaking, producing repeatable output.
- 5: Cycles produce HTTP 422, code `cycle_detected`, and no misleading partial plan.
- 5: malformed input, duplicate task names, and unknown dependency names produce controlled HTTP 400 JSON errors without stack traces.
- 2: `GET /health` provides the required liveness response.

Use additional examiner-created examples; do not rely exclusively on the learner's tests.

### 3. Automated verification — 20 points

- 8: Required normal and edge cases have focused automated coverage with meaningful assertions.
- 5: At least one endpoint-level test exercises serialization, status, and response behavior; planner-level tests remain useful and separate.
- 4: Tests are deterministic, isolated, and fail for a relevant defect rather than merely exercising lines.
- 3: The recorded initial red state and final full-suite evidence are credible and consistent with the submitted work.

### 4. Engineering design and iteration — 15 points

- 6: Planning logic is separable from HTTP transport and validation responsibilities are understandable.
- 4: Errors have stable machine-readable codes and useful bounded messages; internal stack traces do not escape.
- 3: One design decision and a plausible rejected alternative discuss consequences rather than only preferences.
- 2: The reflection describes a concrete feedback-driven change or learning from the iteration.

### 5. Reproducibility and documentation — 10 points

- 4: Clean setup, start, and full-test commands work as documented with dependency versions bounded by a manifest or lock file where the ecosystem supports it.
- 3: The README accurately documents the contract, an example request, layout, and known limitations.
- 2: `evidence/test-output.txt` identifies the command and shows a complete, passing run for the submitted version.
- 1: No credentials, secrets, irrelevant build products, or machine-specific assumptions are required.

### 6. Comprehension — 15 points

Score the eight answers for reasoning tied to the submission, not keyword matching:

- Q1 (2): Names three distinct non-algorithm obligations, such as input contract, transport/error behavior, reproducibility, observability, or maintainability, with concrete evidence.
- Q2 (2): Distinguishes user-visible acceptance evidence from focused planner-unit evidence and explains their complementary failure localization or coverage.
- Q3 (2): Connects deterministic tie-breaking to a stable observable contract and a credible client, test, debugging, caching, or operational consequence.
- Q4 (2): Separates parse failure, contract/domain validation failure, and unsatisfiable valid-domain input; proposes client actions consistent with the responses.
- Q5 (2): Traces a real submitted edge case across boundaries and cites a test capable of catching a regression.
- Q6 (2): Limits liveness claims appropriately and identifies a relevant distinct signal such as readiness, latency/error metrics, dependency checks, or structured logs.
- Q7 (1): Justifies a genuinely deferred feature from scope and identifies a meaningful contract question.
- Q8 (2): Limits the conclusion to the observed slice and names further evidence needed for broader course or production claims.

Generic answers detached from the implementation receive at most half credit for that prompt. Contradictory or unsupported claims receive no credit.

## Decision rule

- **Pass:** at least 75/100, no critical condition, reproducible core behavior, and at least 9/15 in comprehension.
- **Revise:** below the pass threshold or blocked by a learner-correctable issue; report exact failed checks and retain evidence.
- **Blocked:** evaluation cannot be completed for an examiner-side reason or required authorized material is unavailable; do not infer failure or success.

A pass authorizes only the deterministic control plane to record completion of `kickoff_dependency_planner_vertical_slice_v1`. It must leave `course_5bf62d4dddae9f5a6b22345e1e5aa955` incomplete.
