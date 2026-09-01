# Study task: build semantic software another engineer can trust

> Artifact provenance: course-manager-authored for `managed_unit_01_lambda_evaluator`.  
> Validation label: `LEARNER_SAFE_PREPARED`; learner completion has not been validated.

## Goal

Implement the evaluator specified in `COURSE_BRIEF.md`, test it as a collection of cooperating components, and leave reproducible evidence. Construct terms directly through the AST; do not build a parser.

## Required operations

Expose the following conceptual operations using idioms appropriate to your language:

```text
free_vars(term) -> set of names
alpha_equivalent(left, right) -> boolean
substitute(term, variable, replacement) -> term
step(term) -> Stepped(term) | IsValue | IsStuck(reason)
run(term, fuel) -> Value(term, steps)
                 | Stuck(term, steps, reason)
                 | OutOfFuel(term, steps)
```

You may adjust argument order or type names, but preserve the distinctions and behavior. `fuel` must reject negative input or make it unrepresentable.

## Required repository shape

Place your work in a `submission/` directory with:

```text
submission/
  README.md
  DECISIONS.md
  EVIDENCE.md
  COMPREHENSION_RESPONSES.md
  src/                 implementation
  tests/               automated tests
```

Language-standard project metadata may sit alongside these paths. Generated caches and build products are not deliverables.

`README.md` must state the language/runtime version and give one bounded, noninteractive command that runs all tests from a clean checkout. `EVIDENCE.md` must record that exact command, its exit status, and a concise test-result summary. Do not claim a result you did not observe.

In `DECISIONS.md`, briefly record:

- the AST and set representations;
- the exact deterministic fresh-name policy and avoid set;
- how alpha-equivalence is decided;
- the result types for one step and bounded execution; and
- one rejected design choice with its tradeoff.

## Work sequence

1. Define the AST and a readable structural printer used in diagnostics.
2. Implement `free_vars` and test shadowing, nested binders, and both application branches.
3. Implement alpha-equivalence without relying on the literal equality of binder names.
4. Implement substitution in stages: variables, applications, shadowing, safe descent, then alpha-renaming.
5. Implement exactly one left-to-right call-by-value step.
6. Build `run` by repeatedly using `step` while accounting for successful reductions only.
7. Add interaction and boundary tests, then write the decision and evidence files.
8. Respond to every prompt in `COMPREHENSION.md` in your own words.

## Test obligations

Use deterministic automated tests. Cover all of these behavior classes:

- free, bound, and shadowed occurrences;
- alpha-equivalent terms with nested shadowing, and near-misses involving a free variable;
- substitution when the target is absent;
- substitution stopped by a binder that shadows the target;
- substitution that safely enters an unrelated binder;
- substitution that must alpha-rename to avoid capture;
- deterministic freshness when several candidate names are already used;
- beta-reduction only after the argument is a value;
- left-to-right reduction when both sides can step;
- a value at zero fuel;
- a reducible term at zero fuel;
- exact exhaustion after multiple steps;
- a stuck open term distinct from an exhausted term; and
- at least one defect you introduced or anticipated, with a regression test named for its behavior.

For structural results involving generated binders, test alpha-equivalence as well as any intentionally promised canonical name. Tests must terminate and must not use network access.

## Constraints

- Keep the implementation focused on the grammar in the brief.
- Do not add parsing, type checking, effects, primitives, or optimization.
- Do not use host-language evaluation to implement lambda-calculus evaluation.
- Do not mutate global fresh-name state; repeated calls with identical inputs must return identical results.
- Do not treat variables as values or reduce beneath an abstraction.
- Do not add a third-party library solely to perform the semantic core.
- Do not retrieve external course materials for this unit.

## Completion check

Before stopping, confirm that a fresh process can run the documented command, the command has a bounded completion time, all behavior classes above are represented by named tests, the recorded evidence matches the run, and every requested file is present. If the timebox expires, preserve the failing output and list the unfinished requirement rather than describing the unit as complete.
