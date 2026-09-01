# Independent examiner rubric — kickoff linear-system component

This rubric applies only to **Linear Systems as a Tested Software Component**. Passing it is evidence about this bounded unit, never evidence of completing MIT 18.06 or a full linear algebra course.

## Evidence and execution rules

Score the captured `submission/` artifacts and worker-harness execution, not learner or agent claims. Run tests in an isolated attempt workspace with Python 3.11, bounded time, captured stdout/stderr, and no network. The examiner may add deterministic black-box tests. Do not import artifacts from other attempts or expose examiner tests to the learner view.

Before scoring, record file hashes, the exact commands, exit statuses, and test logs. Only the worker-controlled validator may promote job state.

Critical conditions:

- If `linear_solver.py` cannot be imported or `solve` cannot run, the maximum score is 40.
- If the core solve is delegated to a library, subprocess, remote service, or hard-coded case table, the maximum score is 30.
- If required learner-authored tests do not execute, the maximum score is 60.
- If the implementation mutates caller input on a valid call, the maximum score is 70.
- A unit pass requires at least 75/100, at least half credit in sections 1 and 2, no unauthorized dependency or network behavior, and successful harness validation.

## 1. Mathematical behavior — 28 points

- **Unique systems (12):** Correct solutions within a justified scale-aware tolerance for deterministic integer and non-integral cases of several sizes.
- **Pivot-dependent systems (6):** Correctly handles zero or unsuitable leading pivots by selecting and swapping with an available row.
- **Solution-set classification (10):** Reliably distinguishes an inconsistent singular system from a consistent system with infinitely many solutions and raises the specified public exception in each case.

Use at least one black-box case absent from the learner's tests in each subcategory. Check `A x` against `b` independently; do not reuse implementation helpers as the oracle.

## 2. Numerical method and tolerance — 17 points

- **Elimination structure (6):** Implements forward elimination with partial pivoting and a valid unique-path back substitution.
- **Default tolerance (5):** Deterministic, tied to floating-point precision and problem scale, and applied coherently to pivot and rank decisions.
- **Scaling behavior (4):** Equivalent systems at materially different nonzero scales retain appropriate classification and solution behavior within reasonable educational limits.
- **Claims (2):** Documentation avoids claiming that partial pivoting or a small residual proves forward accuracy or production robustness.

Award at most 7/17 if the default is only an unexplained fixed absolute constant. Do not demand agreement on one exact formula; judge stated semantics and observed behavior together.

## 3. Interface, validation, and isolation — 14 points

- **Contract (5):** Function, return shape, exceptions, and tolerance semantics match the task.
- **Validation (5):** Empty, ragged, mismatched, boolean, non-real, non-finite, and invalid-tolerance inputs fail deliberately and consistently.
- **Ownership and state (4):** No caller-owned mutation, import-time output or work, hidden global state, or cross-call contamination.

Where multiple built-in exception types are defensible for malformed input, grade consistency with `DESIGN.md`; the two solution-set exception classes are mandatory.

## 4. Learner verification — 15 points

- **Behavioral breadth (6):** Learner tests cover every category explicitly required by the task.
- **Assertion quality (4):** Assertions check numerical results, exception identity, immutability, and residuals strongly enough to catch plausible faults.
- **Determinism and independence (3):** Tests are repeatable, make no network calls, and do not obtain expected results from the code under test.
- **Failure sensitivity (2):** Inspection or mutation testing shows tests fail under at least one plausible pivoting, classification, or indexing defect.

Do not award points merely for test count or a prose statement that tests passed.

## 5. Design and implementation quality — 12 points

- **Readable decomposition (4):** Names and helpers expose the validation/elimination structure without needless framework code.
- **Invariants and reasoning (4):** `DESIGN.md` accurately states processed-column, row-swap, solution-set, and back-substitution reasoning.
- **Complexity and boundaries (2):** Gives a defensible cubic-time analysis, accounts for copied working storage, and states scope limitations.
- **Maintainability (2):** Focused comments, useful public documentation, no dead code, and no expansion into an unrelated matrix package.

## 6. Comprehension — 10 points

Evaluate all twelve responses for causal reasoning rather than terminology alone.

- **Elimination and classification (3):** Correctly connects reversible row operations, invariants, pivots, and singular-system row patterns.
- **Numerical reasoning (3):** Distinguishes residual from forward error and explains both pivoting's value and its limits.
- **Testing and contracts (2):** Gives concrete, valid reasoning about ownership, oracles, mutation sensitivity, and engineering choices.
- **Complexity and production boundary (2):** Correct analysis and specific production safeguards tied to risks.

Suggested conceptual checks for the examiner include: nonzero row scaling preserves the solution set; a contradictory zero-coefficient row signals inconsistency; a free variable in a consistent square system signals non-uniqueness; and a small residual alone can coexist with large forward error for an ill-conditioned system. Accept equivalent precise reasoning.

## 7. Evidence-based reflection — 4 points

- **Concrete evidence (2):** Identifies a real defect or risk and cites a test, failure, inspection result, or before/after observation.
- **Engineering response (2):** Explains a proportionate change and a remaining limitation, rather than asserting generic confidence.

## Score record

Record section scores totaling 100, critical-condition results, harness-validation identity, and a concise evidence citation for every deduction. A passing score recommends only `unit_c473bebd_kickoff_linear_systems_v1` for the control plane's completion transition; course state must remain `IN_PROGRESS`.
