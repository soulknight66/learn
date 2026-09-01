# Design

Provenance: learner-authored offline from the three supplied kickoff documents. Validation label:
`LEARNER_SELF_CHECKED`, not independently validated.

## Model and preconditions

For items in their input order, the program minimizes

\[
f(x)=\frac12\sum_{i=1}^{n} a_i(x_i-d_i)^2
\]

over the equality simplex

\[
C=\{x\in\mathbb R^n:x_i\ge 0\text{ for all }i,\ \mathbf 1^Tx=B\}.
\]

The input contract requires a finite `budget` with \(B\ge0\), a nonempty list of items, finite
targets, finite positive weights, unique nonempty string IDs, a finite tolerance in
\((0,10^{-3}]\), and a non-Boolean integer iteration bound in \([1,10^6]\). Python integers are
mathematically finite; if a valid integer cannot be represented as binary64 during normalization,
the run is classified as a numerical failure rather than mislabeled as malformed JSON.

Validation has deterministic phase precedence:

1. UTF-8/JSON syntax (`INVALID_JSON`);
2. required fields and container shapes (`INVALID_STRUCTURE`);
3. numeric types, Boolean exclusion, and finiteness (`INVALID_NUMERIC`);
4. numeric ranges (`INVALID_RANGE`); and
5. ID type, emptiness, and uniqueness (`INVALID_ITEM_ID`).

Within a phase, root fields use a fixed order and items use array order. Missing IDs are structural;
present but invalid IDs are ID errors. Extra object members are not prohibited by the supplied
conditions and do not enter the normalized model. File-read failure has the separate stable code
`INPUT_READ_ERROR`.

## Convexity, existence, and uniqueness

The Hessian is \(\nabla^2f=\operatorname{diag}(a_1,\ldots,a_n)\). Every weight is positive, so for
every nonzero \(v\), \(v^T\nabla^2f v=\sum_i a_i v_i^2>0\). Thus \(f\) is strictly (indeed,
strongly) convex.

The feasible set is nonempty: \((B/n,\ldots,B/n)\) belongs to it. It is closed and bounded, hence
compact in finite dimensions. Continuity gives existence of a minimum, and strict convexity over a
convex feasible set makes that minimizer unique. At \(B=0\), the same conclusion is immediate
because the feasible set contains only the zero vector.

## Algorithm

The gradient is componentwise \(a_i(x_i-d_i)\). Its Lipschitz constant in the Euclidean norm is the
spectral norm of the diagonal Hessian,

\[
L=\max_i a_i.
\]

Starting from the equal feasible allocation, one update is

\[
x^{k+1}=P_C\!\left(x^k-\frac1L\nabla f(x^k)\right).
\]

The projection sorts a temporary copy of its input in descending numeric order. Prefix sums locate
the active-set size \(\rho\), after which one common threshold \(\theta\) is subtracted and negative
components are clipped to positive zero. The threshold is applied to the unsorted vector, so the
public allocation remains aligned with item IDs. A zero budget is handled directly.

Sorting dominates projection at \(O(n\log n)\) time. Gradient evaluation, stepping, threshold
application, and residuals are \(O(n)\), so one update plus its reported fixed-point check is
\(O(n\log n)\) time and \(O(n)\) additional memory. The implementation recomputes a projected
update to report the residual; it favors a direct correspondence to the contract over caching a
stale value.

## Invariants and termination

In exact arithmetic, the equal initial vector and every projected iterate have nonnegative
components summing to \(B\). The implementation does not turn this mathematical fact into an
unchecked claim: it recomputes

\[
r_{\rm feas}=\max\left(\left|\operatorname{fsum}(x)-B\right|,
\max_i\max(-x_i,0)\right).
\]

It also recomputes the mandated fixed-point residual for the emitted point,

\[
r_{\rm fp}=\left\|P_C\left(x-L^{-1}\nabla f(x)\right)-x\right\|_\infty.
\]

`CONVERGED` is permitted only if both finite residuals are at most the input tolerance. The initial
allocation is checked with `iterations = 0`. Each loop count represents one completed projected
update, and the last permitted update is checked before exhaustion is declared. If either residual
is still too large after that check, the finite final point is returned with `MAX_ITERATIONS`.
Non-finite arithmetic instead raises `NUMERICAL_FAILURE`; exhaustion never hides it.

Other implementation invariants are that allocation order matches input order, every public number
is finite, a normal result has the exact required field sets, and no error path emits a partial
normal result. JSON is fully serialized before its single stream write.

## Module and failure boundaries

`model.py` owns parsing-independent validation, immutable normalized data, the gradient, and the
objective. `projection.py` knows only the simplex algorithm. `solver.py` is a pure bounded
calculation: it does not read, print, or exit. `cli.py` alone reads raw bytes, hashes them, maps
exceptions to status/stream/exit behavior, and serializes compact JSON. `__main__.py` only delegates
to that adapter.

This division keeps invalid external data separate from valid data that exceeds floating-point
capability and from unexpected programmer failures. It also lets solver tests avoid process I/O
while CLI tests exercise the real stream and exit contracts.

## Numerical limitations

All normalized calculations use Python binary64. `math.fsum` is used for the objective and
feasibility totals, but subtraction, multiplication, prefix accumulation, and thresholding still
round. Very large finite operands can produce a deliberate numerical-failure result; large
condition number \(\max a_i/\min a_i\) can make progress in low-weight coordinates slow enough to
exhaust the bound. When \(B\) is tiny relative to the magnitude of the pre-projection vector,
threshold subtraction can lose significant digits. An absolute tolerance also has scale-dependent
meaning. The program reports these limitations honestly rather than outputting non-finite JSON or
claiming convergence.

The output is byte-deterministic for identical raw input bytes on the supported Python version, but
Python's float formatting and arithmetic are still part of that stated environment. A raw-byte hash
distinguishes documents that parse to the same model but differ in whitespace or spelling.

## Fixed activation charge

Consider adding \(\gamma\sum_i\mathbf1[x_i>0]\) with \(\gamma>0\). For the nontrivial case
\(B>0,n\ge2\), take

\[
p=(0,B,0,\ldots),\quad q=(\varepsilon,B-\varepsilon,0,\ldots),\quad
z=\tfrac12(p+q).
\]

For \(0<\varepsilon<B\), the activation charges at \(p,q,z\) are respectively
\(\gamma,2\gamma,2\gamma\). The quadratic Jensen gap is
\(\tfrac18(a_1+a_2)\varepsilon^2\), independent of the targets. Therefore

\[
[f(z)+2\gamma]-\tfrac12([f(p)+\gamma]+[f(q)+2\gamma])
=\frac\gamma2-\frac{a_1+a_2}{8}\varepsilon^2>0
\]

for sufficiently small positive \(\varepsilon\). This violates the convexity inequality. (If the
equality simplex is a singleton, such as \(B=0\) or \(n=1\), its restricted objective is trivially
convex; that does not rescue the general changed model.)

The feasible set and its projection remain convex and unchanged. On any fixed support the charge is
constant and the quadratic subproblem remains convex. Globally, however, support selection is
combinatorial; uniqueness can fail, the smooth gradient ignores jumps at support changes, and the
quadratic fixed-point residual no longer certifies a global optimum of the modified objective.
Consequently the projected-gradient descent, descent, termination-as-optimality, and global
convergence claims all require a new algorithm and new validation argument.

