# Comprehension Responses

Provenance: learner-authored from the supplied kickoff documents and this implementation only.
Evidence label: `LEARNER_SELF_CHECKED`; these responses are not independent validation.

## 1. Convexity of the feasible allocations

Let \(x,y\) be feasible and \(t\in[0,1]\). For every coordinate,
\(tx_i+(1-t)y_i\ge0\) because both terms are nonnegative. For the equality,

\[
\sum_i(tx_i+(1-t)y_i)=t\sum_i x_i+(1-t)\sum_i y_i=tB+(1-t)B=B.
\]

Thus every line-segment point between two feasible allocations is also feasible, which is exactly
the definition of a convex set.

## 2. Strict convexity, existence, and uniqueness

The decisive condition is `weight > 0` for every item. It makes the Hessian diagonal and positive
definite: \(v^T\nabla^2 f v=\sum_i a_i v_i^2>0\) for every nonzero \(v\). The objective is therefore
strictly convex. The simplex is nonempty and compact and the objective is continuous, so an
optimizer exists. Strict convexity on that convex set permits at most one optimizer, hence the
optimizer exists and is unique. `model.py` enforces positivity before constructing a `Problem`.

## 3. Meaning of \(L\) and poor conditioning

For the diagonal quadratic, \(\nabla f(x)-\nabla f(y)=A(x-y)\) with
\(A=\operatorname{diag}(a_i)\). Its Euclidean operator norm is \(\max_i a_i=L\), so the gradient is
\(L\)-Lipschitz and the specified \(1/L\) step controls the steepest-curvature coordinate.

If \(L/\min_i a_i\) is large, the same step is very small relative to low-curvature coordinates.
I would watch the fixed-point residual decline slowly, rounded updates stagnate, and the finite
iteration bound expire even while feasibility remains excellent. The forced-exhaustion test in
`test_solver.py` separates exactly those residuals.

## 4. Why projection sorts but output does not

Sorting exposes which coordinates remain positive after subtracting a shared threshold. Prefix sums
over descending values determine the largest active-set size \(\rho\), and therefore \(\theta\).
That ordering is a mathematical device; it does not rename coordinates. Applying \(\theta\) back to
the original vector preserves the input ID-to-coordinate mapping required by the public contract.
`test_sort_is_internal_and_original_order_is_preserved` checks this distinction.

## 5. Why objective change is not the convergence contract

A small change in objective can result from poor conditioning, floating-point stagnation, or simply
comparing two nearby iterates that are still infeasible or nonstationary. Objective scale also makes
a fixed change threshold ambiguous. The fixed-point residual tests whether one more specified
projected-gradient map would move the point; at a feasible fixed point it expresses the relevant
first-order condition. The feasibility residual separately checks the budget equality and
nonnegativity. `solver.py` allows `CONVERGED` only when both reported values for the emitted point
are finite and at most the requested tolerance.

## 6. Scope of a finite-grid oracle

An independently written grid enumeration can expose wrong objectives, order mistakes, bad boundary
handling, or a solver result worse than a nearby enumerated feasible allocation. My two-item test
uses spacing \(h=0.001\), enumerates all 1001 equality-feasible points, and states that its location
resolution is one grid cell. It proves only which enumerated point is best. It cannot prove
correctness between grid points, for arbitrary real inputs, in higher dimensions, or for all
floating-point edge cases.

## 7. Invariant and metamorphic property

An example-based invariant is that projecting `(-1.0, 0.2, 2.0)` at budget `1.0` returns
`(0.0, 0.0, 1.0)`: every component is nonnegative, the total is one, and clipped components are
exactly zero. It can reveal threshold, clipping, or budget-sum defects.

A metamorphic property is that permuting complete item records must permute allocations by the same
IDs without changing the underlying optimizer. That test can reveal accidental dependence on array
position, failure to restore pre-sort order, or misalignment between weights, targets, and IDs.
The separate common-weight-scaling property probes step-size/gradient consistency.

## 8. Three different failure meanings

Invalid input means no model satisfying the public preconditions was constructed. It exits 2 and
places one stable `INVALID_INPUT` document on stderr. Iteration exhaustion means a valid computation
produced a finite candidate but one or both residuals remain above tolerance; it is useful result
data, so it exits 3 and uses the normal result schema on stdout with `MAX_ITERATIONS`. An unexpected
internal failure indicates a program defect or unclassified runtime problem; it exits 1 and emits a
generic stderr error without leaking an exception or traceback.

Collapsing them would make retry policy, monitoring, evidence review, and caller control flow
ambiguous. In particular, exhaustion must not masquerade as invalid input or convergence.

## 9. Fixed activation charge

The changed objective is generally not convex. For \(B>0,n\ge2\), let
\(p=(0,B)\), \(q=(\varepsilon,B-\varepsilon)\), and \(z=(p+q)/2\). The charge at \(p\) is
\(\gamma\), while it is \(2\gamma\) at both \(q\) and \(z\). For the quadratic part, the difference
between the average endpoint value and the midpoint value is
\((a_1+a_2)\varepsilon^2/8\). Hence

\[
H(z)-\tfrac12(H(p)+H(q))=\gamma/2-(a_1+a_2)\varepsilon^2/8>0
\]

when \(\varepsilon\) is sufficiently small. This reverses the convexity inequality. Fixed-support
quadratic subproblems and the simplex projection survive, but global convexity, uniqueness,
smooth-gradient interpretation at support changes, and projected-gradient global optimality and
convergence claims all need re-evaluation.

## 10. Reproducibility versus validation and course completion

The exact raw-input SHA-256, fixed course/unit/algorithm identifiers, validation label, tolerance,
iteration count, both residuals, status, ordered IDs and amounts, objective, deterministic start,
step, projection tie behavior, and absence of timestamps/randomness all aid reproduction. CLI tests
also compare two complete output byte strings.

Those facts can reproduce a deterministic bug. The residuals and prose are produced by learner
code, and the passing test suite is learner-controlled evidence. Only a separately controlled
validator can independently check the candidate. Even such a pass would cover only this kickoff
unit; the supplied package explicitly does not establish completion of EE364A or the rest of any
course.

