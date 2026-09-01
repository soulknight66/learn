# Study task: Trustworthy Convex Allocation Solver

## Goal and boundary

Build a deterministic, standard-library-only Python 3.11 command-line tool for a single convex allocation model. Keep the mathematical model, projection routine, iterative solver, command-line adapter, tests, and evidence separate. Work offline; the linked website, recordings, textbook, repositories, and assignments are not inputs to this task.

This is one bounded lab. Do not expand it into a general constraint language or claim that it is an official Stanford assignment.

## Model

An input contains a budget \(B\) and \(n\) named items. Item \(i\) has a positive weight \(a_i\) and a target \(d_i\). Compute an allocation \(x\) that solves

\[
\operatorname*{minimize}_{x}\quad
f(x)=\frac12\sum_{i=1}^{n}a_i(x_i-d_i)^2
\]

subject to

\[
x_i\ge 0\quad\text{for every }i,
\qquad
\sum_{i=1}^{n}x_i=B.
\]

Use projected gradient descent. Start from the equal allocation \(x_i^{(0)}=B/n\), let \(L=\max_i a_i\), take a gradient step of size \(1/L\), and project the result onto the budget simplex.

For a vector \(y\) and \(B>0\), the required simplex projection is the following deterministic sort-and-threshold procedure:

1. Sort the components of \(y\) into \(u_1\ge\dots\ge u_n\).
2. Find the largest \(j\) for which
   \[
   u_j-\frac{\sum_{k=1}^{j}u_k-B}{j}>0.
   \]
3. With that index \(\rho\), set
   \[
   \theta=\frac{\sum_{k=1}^{\rho}u_k-B}{\rho},
   \qquad x_i=\max(y_i-\theta,0).
   \]

For \(B=0\), return the all-zero vector. Preserve original item order in every public result; sorting is internal to the projection.

The implementation must have a finite iteration limit. Define the fixed-point residual as

\[
r_{\mathrm{fp}}=\left\|P_C\!\left(x-\frac{1}{L}\nabla f(x)\right)-x\right\|_\infty
\]

and the feasibility residual as

\[
r_{\mathrm{feas}}=\max\left(\left|\sum_i x_i-B\right|,\ \max_i\max(-x_i,0)\right).
\]

Set status `CONVERGED` only when both reported residuals are less than or equal to the input tolerance. Never report convergence after the iteration limit unless both conditions actually hold.

## Interface contract

Run the program from the submission root as:

```text
PYTHONPATH=src python3 -m allocation_solver INPUT.json
```

The input is one UTF-8 JSON object of this form:

```json
{
  "budget": 1.0,
  "items": [
    {"id": "api", "weight": 1.0, "target": 0.8},
    {"id": "batch", "weight": 2.0, "target": 0.4},
    {"id": "search", "weight": 4.0, "target": 0.3}
  ],
  "solver": {"tolerance": 1e-9, "max_iterations": 10000}
}
```

Reject an input unless all of these conditions hold:

- the root and `solver` values are objects and `items` is a nonempty array;
- `budget`, every `weight`, every `target`, and `tolerance` are finite JSON numbers, not booleans;
- `budget >= 0`, every `weight > 0`, and `0 < tolerance <= 1e-3`;
- `max_iterations` is an integer, not a boolean, in the inclusive range 1 through 1,000,000; and
- every item ID is a unique, nonempty string.

A converged run exits 0 and writes exactly one JSON document to standard output. An exhausted run exits 3 and writes the same result shape. The result has exactly these fields:

- `status`: `CONVERGED` or `MAX_ITERATIONS`;
- `allocations`: an array in original input order whose objects have exactly `id` and finite numeric `amount` fields;
- `objective`: the finite objective value at the emitted allocation;
- `diagnostics`: an object with `iterations`, `tolerance`, `fixed_point_residual`, and `feasibility_residual`;
- `provenance`: an object with `course_id`, `unit_id`, `input_sha256`, `algorithm`, and `validation_label`.

Count `iterations` as completed projected-gradient updates; use zero if the initial equal allocation already meets both residual conditions. Compute both reported residuals for the emitted allocation. The provenance values are:

- course ID `course_0cde7309bb43985ccd240c7cb7544b54`;
- unit ID `unit_kickoff_trustworthy_convex_allocation_v1`;
- the lowercase hexadecimal SHA-256 of the raw input bytes;
- algorithm label `projected_gradient_simplex_v1`; and
- validation label `LEARNER_GENERATED_NOT_INDEPENDENTLY_VALIDATED`.

Iteration exhaustion must retain status `MAX_ITERATIONS`, the same validation label, and the final finite diagnostics; it must not masquerade as convergence.

Invalid input exits 2, writes nothing to standard output, and writes exactly one JSON error object to standard error with this shape:

```json
{"status": "INVALID_INPUT", "error": {"code": "INVALID_RANGE", "message": "a stable explanation without a traceback"}}
```

Use stable codes that distinguish invalid JSON, structure, numeric value, range, and item ID. The example code above is illustrative; select the code matching the detected defect and document deterministic precedence when several defects exist.

`iterations` is a nonnegative integer; all other diagnostic values are finite nonnegative numbers, and `tolerance` echoes the input. If a valid input causes a non-finite intermediate or result, exit 4, emit no standard output, and emit this object to standard error:

```json
{"status": "NUMERICAL_FAILURE", "error": {"code": "NONFINITE_INTERMEDIATE", "message": "numerical result is not finite"}}
```

An unexpected internal failure exits 1, emits no standard output or traceback, and writes this object to standard error:

```json
{"status": "INTERNAL_ERROR", "error": {"code": "INTERNAL_ERROR", "message": "internal solver failure"}}
```

Do not include timestamps, random values, absolute paths, or other run-dependent data. Identical input bytes on the same supported Python version must produce byte-identical output.

## Required implementation structure

Submit at least:

```text
README.md
DESIGN.md
VALIDATION.md
src/allocation_solver/__init__.py
src/allocation_solver/__main__.py
src/allocation_solver/model.py
src/allocation_solver/projection.py
src/allocation_solver/solver.py
src/allocation_solver/cli.py
tests/test_model.py
tests/test_projection.py
tests/test_solver.py
tests/test_cli.py
COMPREHENSION_RESPONSES.md
```

Use pure functions for validation, objective/gradient evaluation, projection, and the solver core wherever practical. The core must not read files, print, exit the process, or depend on global mutable state. The CLI owns file I/O and exit-code mapping. Use only the Python standard library for the submitted solver and tests.

When a CLI test starts a subprocess, pass an argument vector rather than a shell string, use a bounded timeout, capture both output streams, place the child in its own process group, and clean up the group on timeout.

## Required verification work

Run the test suite with:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Create deterministic tests that cover:

- simplex projection with zero budget, an already feasible vector, and components clipped to zero;
- a one-item solve, symmetric items, and an optimum on the nonnegativity boundary;
- malformed JSON and every validation category above, including non-finite values accepted by some JSON parsers;
- a finite but overflow-prone valid input producing an honest `NUMERICAL_FAILURE` rather than non-finite JSON;
- forced iteration exhaustion and honest status/exit behavior;
- two identical CLI runs producing identical bytes;
- permutation equivariance after matching allocations by item ID;
- invariance of the optimizer when all weights are multiplied by the same positive constant; and
- comparison against a small, independently written finite-grid oracle, with the grid's approximation limit stated.

`DESIGN.md` must state the model, preconditions, convexity and uniqueness argument, algorithm invariants, asymptotic cost of projection and one iteration, termination rule, module boundaries, and numerical limitations. It must also analyze one change: add a fixed activation charge \(\gamma\sum_i \mathbf{1}[x_i>0]\) for \(\gamma>0\), then identify which convexity and projected-gradient claims do or do not survive.

`VALIDATION.md` must record the commands and environment used, observed exit codes and outcomes, the raw-input hashing rule, and any remaining limitations. Label learner-run evidence `LEARNER_SELF_CHECKED`; do not label it independently validated. Do not invent successful runs.

Answer every prompt in `COMPREHENSION.md` in `COMPREHENSION_RESPONSES.md` using your own reasoning and references to your implementation. Do not copy the prompts into code comments as a substitute for responses.

## Stop condition

Stop when the listed files, deterministic tests, and honest self-check evidence are complete. Do not retrieve external course resources, add unrelated optimization models, or represent this unit as whole-course completion.

---

Document provenance: course-manager-authored from the supplied CSDIY catalog snapshot; mathematical scaffolding and software contract are local to this kickoff, and no linked content was retrieved.
