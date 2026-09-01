# CS242 Programming Languages: bounded kickoff

> Artifact provenance: course-manager-authored from the supplied CSDIY catalog snapshot; no linked content was retrieved.  
> Validation label: `LEARNER_SAFE_PREPARED`; learner completion has not been validated.

## Status and purpose

This is one manager-authored kickoff unit inspired by topics named in a CS242 catalog snapshot. It is not a reproduction of a Stanford assignment, and completing it does not complete CS242. Later course units require separate sourcing and validation.

The unit is designed for an algorithms student who is comfortable making recursive procedures work and now wants to make semantic software reliable: explicit contracts, deterministic behavior, narrow modules, adversarial tests, and reproducible evidence.

## Unit: From Reduction Rules to a Tested Lambda-Calculus Evaluator

Target time is 8 hours; stop after 10 hours and document any unfinished requirement. You will implement a deliberately small evaluator and its tests. Parsing, type checking, optimization, a REPL, and external course readings are outside this unit.

By the end, you should be able to:

- turn inference rules into small, reviewable program components;
- distinguish binding structure from ordinary tree traversal;
- prevent accidental variable capture during substitution;
- make name generation, evaluation order, and failure states deterministic;
- design tests around semantic partitions and component interactions; and
- leave enough commands and decision records for another engineer to reproduce your result.

## Working assumptions

Use a statically typed language already available in your environment. OCaml is preferred because the catalog identifies it as a course language, but another locally installed language is acceptable. State the language and version in your submission. Do not spend the unit installing a new toolchain or retrieving linked course content.

You need recursion, immutable data structures, sets, and a unit-test facility. No third-party dependency is required.

## Semantic reference

### Terms and values

Use a named abstract syntax tree:

```text
t ::= x              variable
    | λx. t           abstraction
    | t t             application

v ::= λx. t           value
```

Applications associate to the left. A term may be open, so your implementation must represent free variables even though well-behaved evaluation examples are often closed.

### Free variables

`FV(t)` is defined structurally:

```text
FV(x)       = {x}
FV(λx. t)   = FV(t) − {x}
FV(t1 t2)   = FV(t1) ∪ FV(t2)
```

Two terms are alpha-equivalent when they differ only in consistent names chosen for bound variables. Free-variable names remain significant.

### Capture-avoiding substitution

`[x ↦ s]t` replaces free occurrences of `x` in `t` with `s`.

- At a variable, replace exactly when its name is `x`.
- In an application, recurse into both children.
- Under `λx`, stop: that binder shadows the variable being replaced.
- Under `λy` where `y ≠ x`, recurse directly only when doing so cannot capture a free variable of `s`.
- If capture is possible, alpha-rename the binder and its bound occurrences to a name fresh for all relevant names, then continue.

Fresh-name choice is observable engineering behavior even though different fresh choices can denote alpha-equivalent terms. Define one deterministic policy and test it. A practical policy chooses the first name in a documented sequence that is outside the union of names that must be avoided.

### Call-by-value small-step evaluation

Use left-to-right call-by-value reduction. The rules are:

```text
t1 → t1'
──────────────
t1 t2 → t1' t2

t2 → t2'    v1 is a value
─────────────────────────
v1 t2 → v1 t2'

v2 is a value
──────────────────────────────
(λx. t12) v2 → [x ↦ v2]t12
```

An abstraction is a value. A variable is not a value. An application that matches no rule is stuck.

### Bounded execution

Evaluation can diverge, so the driver accepts a nonnegative fuel value. One unit of fuel permits one successful small step. Report one of three distinct terminal outcomes:

- `Value(term, steps)` when a value is reached;
- `Stuck(term, steps, reason)` when no rule applies to a non-value; or
- `OutOfFuel(term, steps)` when another step would be required but the budget is exhausted.

The driver must never disguise `OutOfFuel` as `Stuck`, and it must not spend fuel merely checking whether the initial term is already terminal.

## Engineering lens

Keep semantic responsibilities separable. A reviewer should be able to locate the AST, name analysis, substitution, one-step relation, bounded driver, and tests without reverse-engineering a monolith. Prefer explicit result variants over exceptions for normal semantic outcomes. Ensure failure messages identify the term or behavior being checked.

Test the partitions created by the rules, then test their interactions. In particular, easy substitution cases do not exercise capture avoidance, and beta-reduction tests do not by themselves prove left-to-right evaluation or correct fuel accounting.

## Material boundary

This brief, `STUDY_TASK.md`, and `COMPREHENSION.md` are the complete required learner inputs for this kickoff. The catalog also supplied links to course sites, an assignment index and repository, a TAPL landing page, and a course-design paper. Their contents were not retrieved or verified for this unit. The catalog reports no recordings. You are not expected to follow any external link.
