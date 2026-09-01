# Comprehension Prompts

Course ID: `course_94560b3a323bb4da6a3c762995a4958b`  
Unit ID: `kickoff_slp_interpreter_v1`  
Validation label: `PREPARED_UNVALIDATED`

Answer these in your own `COMPREHENSION_RESPONSES.md`. Refer to the specified semantics and explain your reasoning concisely. A bare output or yes/no response is insufficient where a justification is requested.

## 1. State and evaluation order

Trace this program:

```text
Compound(
  Assign("x", Num(4)),
  Print([
    Id("x"),
    Eseq(
      Assign("x", Op(Id("x"), Add, Num(3))),
      Op(Id("x"), Multiply, Num(2))
    ),
    Id("x")
  ])
)
```

State the exact output bytes in an escaped or fenced representation, the final binding of `x`, and the order in which the reads and write of `x` occur.

## 2. Structural analysis versus execution

Consider:

```text
Compound(
  Print([
    Num(1),
    Eseq(Print([Num(2), Num(3), Num(4)]), Num(5))
  ]),
  Assign("z", Eseq(Print([Num(6), Num(7)]), Num(8)))
)
```

What should `max_print_arity` return? Separately, what lines would interpretation emit and in what order? Explain why the analysis can answer its question without predicting execution order or maintaining an environment.

## 3. Failure and already-completed effects

Assume the environment initially has no bindings and trace:

```text
Compound(
  Assign("x", Num(1)),
  Print([
    Eseq(Assign("x", Num(2)), Id("x")),
    Op(
      Eseq(Print([Num(9)]), Num(10)),
      Divide,
      Num(0)
    ),
    Id("x")
  ])
)
```

Identify the error category, exact output that remains, final binding of `x`, and subexpressions that are not evaluated. Relate each observation to the buffering and stop-on-first-error rules.

## 4. Safe arithmetic

Why is checking a signed addition only after evaluating `left + right` unsafe in portable C++? Describe a valid strategy for detecting overflow before or during the operation. Also name the special signed-division overflow case and distinguish it from division by zero.

## 5. AST ownership and invariants

Describe your AST ownership model. Which object owns each child, can nodes be shared, and how are missing children, invalid names, and empty prints prevented or reported? Explain one tradeoff of your design for traversal or future source-location support.

## 6. Tests as specifications

Propose a compact table of at least four tests that together distinguish:

- left-to-right from right-to-left evaluation;
- per-print buffering from streaming partial values;
- a pure `max_print_arity` from one with leaked mutable state; and
- an unbound-name error from a valid zero value.

For each test, name the observable assertion that makes the distinction. Do not rely on console inspection.

## 7. Complexity and depth

Give time and auxiliary-space bounds for interpretation and `max_print_arity` in terms of the number of AST node occurrences `n` and maximum tree depth `h`. State assumptions about environment-map operations and output size. What practical risk remains for a highly skewed AST even if the time bound is linear?

## 8. Extension boundary

Suppose a later unit adds a lexer and parser that attach source spans to AST nodes. Identify which current interfaces should remain stable, which may need extension, and how source spans could improve errors without coupling the interpreter to tokenization. Do not design or implement the parser.

## Provenance

These learner-facing questions were manager-authored for the kickoff specification using only the supplied catalog topic. They contain no answer key or scoring rubric. The snapshot content hash is `c0b01a3547deab67a2c9ce70808ae093949cc577ef4b3208bb40f409922c4189`; no external content was retrieved. `PREPARED_UNVALIDATED` is a preparation label, not a completion result.
