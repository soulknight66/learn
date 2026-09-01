# Independent examiner rubric: managed unit 01

> Artifact provenance: course-manager-authored from the bounded unit specification and supplied catalog snapshot.  
> Validation label: `EXAMINER_ONLY_PREPARED`; this is a validation instrument, not a completed validation result.

This instrument evaluates only **From Reduction Rules to a Tested Lambda-Calculus Evaluator**. It must not be used to infer completion of CS242 or of any official Stanford assignment.

## Examiner procedure

1. Inspect `submission/README.md` and execute its single all-tests command in a clean learner workspace, with network disabled and a bounded timeout.
2. Record the command, exit status, duration, and captured output. A learner's `EVIDENCE.md` is corroborating data, not proof.
3. Inspect source rather than accepting API-name matches or prose claims. Confirm that host-language evaluation and third-party semantic engines are not doing the core work.
4. Add or run independent cases for binding, evaluation order, fuel boundaries, and stuck terms. Compare generated-binder results modulo alpha-equivalence unless the learner explicitly promises a canonical spelling.
5. Score the observable artifact against the criteria below. Report failed gates separately from the numeric score.

## Non-negotiable gates

- **Isolation:** no network retrieval, restricted content, examiner data, or another learner's files appear in the submission.
- **Runnable evidence:** the documented test command is noninteractive, terminates within the harness timeout, and returns a trustworthy exit status.
- **Semantic ownership:** the learner implemented the semantic core; it is not delegated to `eval`, a host interpreter, or an external lambda-calculus package.
- **Scope:** the submission evaluates only the specified calculus and does not substitute unrelated project work.

Failure of Isolation or Semantic ownership means the unit is not validated. If the project cannot build or run for reasons attributable to the submission, award at most 45/100. If the implementation runs but an entire required operation is absent, award at most 60/100.

## Scored criteria (100 points)

### 1. Binding semantics — 30 points

- **Free variables (5):** correct for variables, applications, abstractions, and nested shadowing.
- **Alpha-equivalence (8):** preserves binder relationships through nesting and shadowing while keeping free names significant.
- **Ordinary substitution cases (6):** correct replacement, absent target, application recursion, and shadowing stop.
- **Capture avoidance (8):** renames precisely when needed and avoids capture in nested/adversarial cases.
- **Deterministic freshness (3):** identical inputs yield identical names/results without mutable global-name history.

### 2. Evaluation and bounds — 25 points

- **One-step relation (10):** implements left-to-right call-by-value, does not reduce beneath lambdas, and beta-reduces only with a value argument.
- **Outcome distinctions (6):** value, stuck, and out-of-fuel are explicit and semantically distinct.
- **Fuel accounting (7):** only successful reductions consume fuel; zero and exact-boundary cases are correct; step counts match.
- **Termination control (2):** a divergent term is safely bounded without recursion or loop leakage beyond the budget.

### 3. Test quality — 20 points

- **Partition coverage (8):** named tests exercise every test obligation in `STUDY_TASK.md`.
- **Adversarial interactions (6):** tests combine renaming with beta-reduction, distinguish free from bound lookalikes, and expose evaluation order.
- **Boundary precision (4):** zero, exact, one-short, stuck, and deterministic-repeat cases make off-by-one failures visible.
- **Regression value (2):** at least one clearly named test is tied to a plausible or observed defect.

### 4. Software-engineering quality and evidence — 15 points

- **Separation and contracts (5):** AST, name analysis, substitution, step, driver, and tests have reviewable responsibilities and explicit result contracts.
- **Readability and diagnostics (3):** naming, formatting, and failure output make semantic defects localizable.
- **Reproduction (4):** version, clean command, exit status, and result summary are present and examiner-reproducible.
- **Decision record (3):** all requested choices and one rejected alternative are explained with concrete tradeoffs.

### 5. Comprehension — 10 points

Award credit for reasoning, not merely final notation. Expected anchors:

- **Prompt 1 (1):** the free-variable result is `{y, z}`; the response accounts for the outer `x` binder and the inner `y` binder without deleting the free `y` in the other branch.
- **Prompt 2 (2):** the binder must be renamed to a fresh name before substitution; a valid shape is alpha-equivalent to `λa. y a`, with `a` fresh under the learner's policy.
- **Prompt 3 (1):** examples preserve a consistent binder correspondence through shadowing; the near-miss changes binding depth or makes an occurrence free.
- **Prompt 4 (2):** the trace uses left-to-right call-by-value beta steps, reaches `λw. w`, and charges one fuel unit per actual transition.
- **Prompt 5 (1):** a free variable or unsuitable open application can be stuck; a reducible or divergent term at an insufficient bound is out of fuel; the diagnostic consequences differ.
- **Prompt 6 (1):** the avoid set prevents collisions with relevant names in the body/replacement and the substitution target; the explanation connects omission to capture, accidental rebinding, or nondeterminism.
- **Prompt 7 (1):** the method tracks binder correspondence or uses a nameless comparison; free names are compared literally.
- **Prompt 8 (1):** the response names a concrete interface mismatch, an interaction test, and reproducible command/output evidence.

## Independent probe set

Translate these probes into the learner's AST/API. Do not require a particular printed binder name.

1. `FV(λx. (x (λx. (x y))))` must be `{y}`.
2. `λx. λy. x` is alpha-equivalent to `λa. λb. a`, but not to `λa. λb. b`.
3. `[x ↦ y](λy. x)` must keep the inserted `y` free and return a term alpha-equivalent to `λa. y` for fresh `a`.
4. `[x ↦ λz. z](λx. x y)` must leave the term unchanged because the binder shadows `x`.
5. In an application whose function and argument can both step, the first step must change only the function.
6. `(λx. x) (λy. y)` at fuel `0` is `OutOfFuel` with zero steps; at fuel `1` it is `Value(λy. y, 1)`.
7. A lambda at fuel `0` is `Value` with zero steps.
8. A free variable at any positive fuel is `Stuck` with zero steps, not `OutOfFuel`.
9. Repeating a capture-avoiding substitution after unrelated evaluator calls must produce structurally identical output under the promised deterministic policy.
10. A standard self-application loop must return `OutOfFuel` at the exact supplied budget and report that many successful steps.

## Validation decision

- **Validated:** all non-negotiable gates pass, score is at least 80/100, Binding semantics is at least 21/30, and Evaluation and bounds is at least 18/25.
- **Revision required:** any gate or threshold fails. Return criterion-level findings and captured evidence; do not promote course status.

Even a validated result applies only to `managed_unit_01_lambda_evaluator`. The course completion effect is always none.
