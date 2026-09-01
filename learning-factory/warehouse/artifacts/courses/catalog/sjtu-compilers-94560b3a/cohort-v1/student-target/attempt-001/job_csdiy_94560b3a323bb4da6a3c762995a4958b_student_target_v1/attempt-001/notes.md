# Kickoff Unit Notes

Course unit: `kickoff_slp_interpreter_v1`  
Learner validation label: `LEARNER_SELF_CHECKED_UNVALIDATED`

## Working model

- Syntax is immutable data. Execution owns the mutable environment and output
  destination; analysis owns neither.
- `Eseq` is the key interaction case because expression evaluation can perform
  statement effects before returning a value.
- “Stop on error” does not imply rollback. Assignments and nested output that
  completed before the error remain observable.
- Per-print buffering delays only that print's own line. It does not buffer a
  nested print performed while evaluating one of its expressions.

## Concrete hypotheses and experiments

1. Hypothesis: local return values are enough for a pure arity traversal.
   Experiment: analyze a maximum-4 tree, a no-print tree, then the first shape
   again. Observed results were 4, 0, and 4, supporting the absence of leaked
   traversal state.
2. Hypothesis: left-to-right behavior is best tested with state changes, not
   only arithmetic literals. Experiment: both operands and later print
   expressions assign `x`. The asserted output is `"-1 4 4\n"` with final
   `x = 4`; reversing either order changes an observable.
3. Hypothesis: buffering a vector of values until every expression succeeds
   preserves nested effects while suppressing the failed outer line.
   Experiment: an outer print assigns `x = 2`, emits `9` from a nested `Eseq`,
   then divides by zero. The result retains only `"9\n"` and `x = 2`.
4. Hypothesis: precondition checks cover arithmetic boundaries without first
   invoking signed overflow. Experiment: all four overflow categories are
   asserted, while multiplication/addition/subtraction at `INT64_MIN` and
   `INT64_MAX` boundaries are also asserted as successful where valid.
5. Hypothesis: an injectable `std::ostream` makes both exact-byte testing and
   output errors controllable. Experiment: an `ostringstream` captures normal
   bytes; a rejecting stream buffer produces `OutputFailure` while preserving
   evaluation effects.

## Engineering lessons

- A structured result needs both an error category for callers and context for
  diagnosis. Comparing only message text would make tests and extensions
  brittle.
- Assignment has its own commit boundary: evaluate the right side first, then
  mutate the named target. Other effects inside the right side are already
  committed under this language's semantics.
- Checking only happy-path values would miss the most C++-specific risk here:
  undefined signed overflow. Boundary-success tests complement failure tests.
- Immutable shared nodes are convenient for direct AST fixtures, but complexity
  must be stated in node occurrences because a shared subtree can be reached
  more than once.
- Recursive code is clear for this bounded unit, while native stack exhaustion
  remains a production concern for adversarially deep future input.

## Scope boundary

I attempted only the straight-line interpreter kickoff. I did not implement or
study a lexer, parser, type checker, optimizer, IR, LLVM integration, or an
external course framework. Local self-check results are not an independent
completion decision and do not establish completion of the broader course.

## Provenance

These notes use only the three supplied learner-safe course files:
`COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`.
