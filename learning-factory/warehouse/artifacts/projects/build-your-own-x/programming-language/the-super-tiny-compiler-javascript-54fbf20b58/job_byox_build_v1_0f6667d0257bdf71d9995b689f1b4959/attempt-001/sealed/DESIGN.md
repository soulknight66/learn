# Sealed design notes

This file contains suggested answers to `DESIGN_QUESTIONS.md`. It is evaluator material and must not
be exposed with the initial learner view.

## Tokens and syntax

1. When the scanner sees `/`, it peeks exactly one character. A second `/` consumes a comment up to,
   but not including, the newline; otherwise the original character becomes `SLASH`. This keeps
   newline accounting in the main scanner loop.
2. Positions identify the next unread character. Empty input therefore ends at 1:1. Consuming a
   newline increments the line and sets the next column to 1. Treating CRLF as one logical newline
   avoids surprising Windows-source locations, while a lone CR is also whitespace with a defined
   position update.
3. The reference implementation fails at the first syntax error. A multi-error extension could
   synchronize at `;`, `}`, or the beginning of a statement keyword, but it must guarantee that each
   recovery consumes at least one token.
4. The finite, conventional precedence table maps clearly to layered recursive-descent methods. A
   Pratt parser would become more attractive if Pebble gained many postfix or user-defined
   operators, because adding a binding-power entry is then more local than adding grammar methods.

## Semantics

5. Blocks do not scope in this version. That makes a binding introduced conditionally visible only
   if the declaration actually executes, which demonstrates why name validity is a runtime concern.
   Lexical blocks would be a sensible extension but would require environment enter/leave bytecode
   and a policy for shadowing.
6. Duplicate definitions and undefined reads or updates fail at runtime. Static rejection would
   incorrectly reject some path-dependent programs or require a control-flow analysis beyond this
   exercise. The compiler still rejects malformed AST shapes rather than treating them as language
   errors.
7. JavaScript would otherwise leak string concatenation, truthiness, `NaN`, infinities, loose
   equality, and conversions such as `true + 1`. Every Pebble operator checks its operand types
   before applying a host operator; equality uses strict comparison after validating Pebble values.
8. The evaluator charges statement dispatch and every loop condition attempt. In particular, an
   empty-body infinite loop still spends budget while checking its condition. The VM independently
   charges every dispatched instruction.

## Compiler and VM

9. Compiling any expression changes abstract stack height by +1. Compiling a complete statement has
   net change 0: define, update, emit, and conditional jump instructions consume their expression
   value. Each branch must end at the same height at which it began. A debug compiler can track an
   integer height and assert this at statement and merge boundaries.
10. An `if` without `else` patches its false jump to the first instruction after the consequent. An
    `if` with `else` first patches the false jump to the else entry, then patches an unconditional
    jump over that else block to the final continuation. Neither destination is known until the
    intervening instructions have been emitted.
11. A separate validation pass provides failure atomicity: malformed bytecode fails before any emit
    or variable update. It also simplifies the hot dispatch loop. Integrated checks use less code
    and can support streaming, but can expose partial output before a late structural failure. The
    reference favors prevalidation plus small defensive assertions in execution.
12. Test operand presence with an own-property check, not truthiness. `0` is a valid constant index
    and jump address. Then validate the property's type and range according to the opcode.
13. Compilation builds fresh arrays rather than attaching data to the AST. Execution creates fresh
    stack, environment, and output structures and treats constants/instructions as read-only. That
    makes compiling or executing the same object repeatedly independent.

## Testing and evolution

14. Parse expressions such as `1 + 2 * 3 == 7` and inspect the AST before testing their result. A
    separate evaluation test can construct the expected AST manually, preventing the parser and
    evaluator from hiding the same associativity defect.
15. Compare success outputs exactly and failures by exported error class plus a stable category or
    message fragment. Full message equality makes harmless diagnostic improvements unnecessarily
    breaking.
16. A generator can declare a fixed set of variables first, build only expressions from those names,
    and omit loops; alternatively it can generate loops around a nonnegative counter that is reduced
    exactly once each iteration. Bound AST depth, statement count, and numeric magnitude as well.
17. Strings would add scanner escape rules, a `StringLiteral` AST node, value validation, a decision
    about `+`, constants-pool support, VM operator behavior, formatting in diagnostics, generator
    cases, and tests for invalid escapes and mixed-type comparisons. This cross-phase cost is why the
    base language leaves them out.

