# Study Task: Build a Reliable Bisection Component

Create a small, reproducible Julia project named `ReliableBisection`. Treat it as a library component that another engineer must be able to call, test, and diagnose—not as a one-off script.

## 1. Specify before coding

In `DESIGN.md`, define the public contract for a function with this conceptual interface:

```julia
bisect(f, a, b; atol, rtol, maxiter)
```

State accepted numeric endpoint types, tolerance rules, assumptions about `f`, whether and when endpoints are evaluated, the bracket evidence required, and every observable outcome. Include distinct outcomes for convergence, an endpoint root, invalid input, a missing bracket, a non-finite function value, iteration-budget exhaustion, and floating-point stagnation. Say whether outcomes are returned or thrown and keep that policy consistent.

Define the mixed absolute/relative interval criterion you intend to use, including its scale term. Explain separately what, if anything, a function residual means in your API. Do not rely on a residual as an unstated substitute for the interval contract.

## 2. Design the evidence first

Before implementing the loop, add a short test inventory to `DESIGN.md`. For each required behavior below, name the input class, the expected observable property, and why a routine written from ideal-real-number pseudocode might fail there.

Use deterministic examples; no random seed, time, network, or machine-specific path may affect pass/fail.

## 3. Implement the component

Place library code under `src/` and tests under `test/`. Use Julia's standard `Test` library and provide a conventional `Project.toml` plus `test/runtests.jl`.

Your implementation must:

- validate interval order, finite endpoints, nonnegative finite tolerances, and a positive iteration budget;
- handle an exact zero at either endpoint explicitly;
- reject a non-bracketing interval without using arithmetic that can overflow merely while comparing endpoint signs;
- maintain and make auditable a bracket invariant after each accepted update;
- compute an interior candidate without spuriously producing a non-finite value when the finite endpoints admit an appropriate finite midpoint;
- evaluate `f` deliberately, avoid unnecessary repeated endpoint evaluations, and handle a non-finite function result explicitly;
- combine the documented absolute/relative interval rule with an iteration bound;
- detect when the candidate cannot make representable progress; and
- return enough structured information to identify the outcome and inspect at least the estimate, final interval, iteration count, and final function evidence where applicable.

Avoid global mutable state, hidden I/O, external packages, and broad exception handling. Add concise docstrings and keep numerical policy separate enough from presentation that tests can inspect it directly.

## 4. Required test groups

Write focused tests for all of these groups:

1. A routine continuous example with a known bracket and a checkable interval property.
2. A root equal to the left endpoint and a root equal to the right endpoint.
3. Reversed or equal endpoints, negative or non-finite tolerances, non-finite endpoints, and a nonpositive `maxiter`.
4. Finite endpoint values that do not bracket a root.
5. A function that returns `NaN` or an infinity during evaluation.
6. An iteration limit too small to meet the requested interval criterion.
7. Adjacent floating-point endpoints or another case in which no interior representable progress is possible.
8. Very large finite endpoints, including an opposite-sign pair whose mathematical midpoint is finite.
9. At least one `Float32` case and one `Float64` case, with assertions appropriate to each type.
10. An instrumented function that makes the claimed evaluation behavior observable.

Assert contracts and invariants rather than only comparing one final decimal. A test that merely prints output is not evidence.

## 5. Run a bounded experiment

Create `EXPERIMENT.md` containing one compact table from three deterministic runs at meaningfully different scales. Record inputs, tolerances, outcome, iterations, final interval width, a residual if your result exposes one, and Julia version. Add a paragraph distinguishing what the table demonstrates from what it does not demonstrate.

## 6. Deliverables

Submit only the project and your own evidence:

```text
ReliableBisection/
├── Project.toml
├── README.md
├── DESIGN.md
├── EXPERIMENT.md
├── src/
│   └── ReliableBisection.jl
└── test/
    └── runtests.jl
```

`README.md` must give the exact offline test command, supported Julia version, a minimal usage example, and a limitations section. Your final handoff should report the command's exit status and identify any unmet requirement honestly.

After the implementation is stable, answer every prompt in `COMPREHENSION.md`. Refer to exact tests, result fields, or short source locations so that your claims can be checked.
