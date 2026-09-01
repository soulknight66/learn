# Bounded first-unit submission

I completed the source-level kickoff unit for `ReliableBisection`, not the full
course. The package contains the requested project metadata, README, design,
experiment plan, implementation, and deterministic tests. The exact offline
test command exited 127 because the environment has no `julia` executable.
Accordingly, I do not claim that the tests pass or that the measured experiment
is complete.

## Handoff status

- Present: all six requested project paths, a structured seven-state result API,
  overflow-aware midpoint/width policy, cached evaluation evidence, and 13
  focused testsets covering the required groups.
- Limited validation: a file/layout/token check exited 0.
- Unmet: Julia parsing/execution, a supported version observed in practice, and
  three measured experiment rows.
- Exact test command: `julia --project=. -e 'using Pkg; Pkg.test()'` from
  `ReliableBisection/`.
- Exact test exit status: 127 (`julia: command not found`).

## Comprehension responses

### 1. Bracket invariant

For every nonterminal loop state, `left < right`; both cached endpoint values
are finite and nonzero; and they have strict opposite signs. The update at
`src/ReliableBisection.jl:241` replaces the right endpoint when the left and
candidate signs differ, otherwise replaces the left, then asserts the invariant
at line 247. Testset `each invariant update branch` (`test/runtests.jl:25`)
chooses roots on opposite sides of the first midpoint and checks the exact final
interval plus endpoint signs. Those assertions would fail if either branch were
reversed. They have not been executed in this environment.

### 2. Floating-point midpoint expressions

Rounding occurs after individual operations, and an intermediate can overflow
even when the mathematical result is finite. In particular,
`left + (right-left)/2` forms an infinite difference for the two finite extreme
endpoints. `_midpoint` (`src/ReliableBisection.jl:75`) divides each endpoint
before adding when their numeric signs differ. Testset `large finite
opposite-sign endpoints` (`test/runtests.jl:201`) requires a finite zero estimate
for `[-floatmax, floatmax]`. That one authored example checks the promised case;
even if it passes, it does not prove universal midpoint safety.

### 3. Width versus residual

A narrow bracket can localize a root under continuity while the evaluated
residual remains large for a steep function such as `10^12*(x-r)`. Conversely,
a very flat function such as `10^-12*(x-r)` can have a tiny residual while `x`
is still far from `r`. `status == CONVERGED` uses only the documented interval
rule (or an observed exact zero). `f_estimate` is stored separately and can be
`nothing`; it is never compared with a residual tolerance.

### 4. Mixed stopping scale

The scale is `max(abs(left), abs(right))`, so the relative term grows with the
current endpoint magnitude. Near zero that scale shrinks, and `atol` provides a
units-based floor. Testset `absolute floor is visible near zero`
(`test/runtests.jl:244`) uses one tiny bracket twice: `atol=3e-12` should accept
the initial interval at iteration zero, while the relative-only case must first
evaluate the exact midpoint root.

### 5. Stagnation

Stagnation means `_midpoint(left,right)` equals a current endpoint, so an
interior representable candidate was not produced. For `1.0` and
`nextfloat(1.0)`, there is no `Float64` strictly between them. Repeating the same
rounded arithmetic with a larger `maxiter` cannot change that set of values.
Testset `representational stagnation` (`test/runtests.jl:175`) expects zero
interior iterations and only two endpoint calls despite a budget of 100.

### 6. Evaluation count

An ordinary path evaluates each endpoint once, then one new candidate per
iteration: two ordinary iterations therefore mean four calls. Testset
`observable evaluation policy` (`test/runtests.jl:271`) asserts the exact call
sequence `[1.0, 2.0, 1.5, 1.25]` and stored count 4. A left endpoint root returns
after one call; a right endpoint root requires the left call and then the right,
so it returns after two. Both sequences are also asserted there. These are
authored expectations, not observed passing results here.

### 7. Invalid and runtime outcomes

A non-finite endpoint returns `INVALID_INPUT` with detail
`:nonfinite_endpoint` and zero evaluations. A midpoint `NaN` returns
`NONFINITE_FUNCTION` with detail `:interior_value`, the failed candidate,
iteration/evaluation counts, and the `NaN` evidence. A caller can switch on the
enum and detail: repair the input in the first case, or diagnose/replace the
function or bracket in the second. No message parsing is required. The relevant
tests start at `test/runtests.jl:82` and line 129.

### 8. Large magnitude

The large test uses `[-floatmax(Float64), floatmax(Float64)]` and `identity`.
The dangerous intermediate is `right-left` in the otherwise common expression
`left + (right-left)/2`; it overflows. The assertions require a `CONVERGED`
exact-root result, a finite estimate equal to zero, one iteration, and three
evaluations. This checks the component's observable promise for that selected
extreme pair.

### 9. `Float32` versus `Float64`

Testset `Float32 and Float64 retain the same contract`
(`test/runtests.jl:221`) chooses `16*eps(T)` rather than one fixed decimal
tolerance and checks that endpoints and estimate retain `T`. The width bound and
rounded `sqrt(T(2))` comparison are therefore type-aware. Status, structured
fields, strict-sign invariant, validation order, and evaluation-count policy
should be type-independent. Runtime comparison remains pending.

### 10. Proportional correctness claim

The strongest current claim is that the source, written contract, and
deterministic test inventory are statically traceable to every requested
behavior, and that the required file/token check passes. I cannot claim that
the Julia code parses or that any behavioral test passes because Julia was
unavailable. Even after those tests pass, they would not justify correctness
for every floating-point interval or arbitrary function, and they would not
verify the caller's crucial continuity assumption (nor uniqueness or good
conditioning of the root).
