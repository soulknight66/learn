# Study Task: Engineer a Straight-Line Program Interpreter

Course ID: `course_94560b3a323bb4da6a3c762995a4958b`  
Unit ID: `kickoff_slp_interpreter_v1`  
Target language: C++17  
Timebox: 10 hours  
Validation label: `PREPARED_UNVALIDATED`

## Mission

Build a small C++17 library that represents and executes a straight-line language, plus a pure analysis named `max_print_arity`. Treat the project as a software component that another engineer could build, test, and extend. There is no parser: programs are assembled as AST values in C++ tests or fixtures.

## Language model

Support exactly these forms:

```text
Statement  := Compound(Statement, Statement)
            | Assign(Name, Expression)
            | Print([Expression, ...])

Expression := Id(Name)
            | Num(Int64)
            | Op(Expression, Operator, Expression)
            | Eseq(Statement, Expression)

Operator   := Add | Subtract | Multiply | Divide
```

`Name` must be a nonempty identifier matching `[A-Za-z_][A-Za-z0-9_]*`. A `Print` contains at least one expression. Child nodes must not be null or otherwise absent. Enforce these invariants at construction or report a structured invalid-AST error before evaluation. Your representation must not rely on raw owning pointers.

## Required execution semantics

The environment begins empty and maps names to signed 64-bit integers.

- `Compound(a, b)` executes `a` completely and then `b`.
- `Assign(name, exp)` evaluates `exp` and stores its value under `name` only if that evaluation succeeds.
- `Id(name)` reads the current value. Reading an unbound name is an error.
- `Num(value)` evaluates to `value`.
- `Op(left, op, right)` evaluates the left operand completely, then the right operand completely, then applies `op`.
- `Eseq(stm, exp)` executes `stm`, including its state and output effects, and then evaluates `exp` in the resulting environment.
- `Print(exps)` evaluates its expressions from left to right in the shared environment. After every expression succeeds, it emits their decimal values on one line, separated by one ASCII space, followed by `\n`.

Buffer the values for each individual `Print`: if one of that print's expressions fails, that print emits no partial line. Effects already completed while evaluating earlier expressions—including output from a nested `Eseq`—remain observable. Stop the program at the first error; do not evaluate later operands, expressions, or statements.

Arithmetic is checked signed 64-bit arithmetic. Report an error for overflow in addition, subtraction, or multiplication; division by zero; and the `INT64_MIN / -1` overflow case. Do not invoke C++ signed-overflow undefined behavior.

Expose a programmatic execution boundary that returns either a successful result or a structured error category with useful context. The exact C++ error mechanism is your design choice, but expected program errors must not abort the process or escape the public boundary as uncaught exceptions. Make the output destination injectable rather than hard-wiring library code to `std::cout`.

## Required structural analysis

Implement `max_print_arity` for a statement. It returns the largest number of expressions in any `Print` occurring anywhere in the tree, including prints inside `Eseq` expressions and inside operands of `Op`. It returns zero when the tree has no print statement.

The analysis must not execute the program, read or change an environment, emit output, or reuse stale mutable traversal state. Document its time and auxiliary-space complexity in terms of AST size and depth.

## Engineering deliverables

Submit all of the following:

1. A C++17 AST and interpreter implementation with a public library interface.
2. The `max_print_arity` analysis.
3. A top-level `CMakeLists.txt` that builds without downloading dependencies.
4. Automated tests registered with CTest.
5. A small executable or test fixture demonstrating a nontrivial program containing `Assign`, `Compound`, `Print`, `Op`, and `Eseq`.
6. `README.md` with prerequisites and exact configure, build, and test commands.
7. `DESIGN.md` describing:
   - AST ownership and construction invariants;
   - separation of syntax, execution state, output, and analysis;
   - the error model and effect behavior on failure;
   - evaluation-order guarantees;
   - interpreter and analysis complexity; and
   - one extension seam for a future parser without implementing it.
8. `COMPREHENSION_RESPONSES.md` containing your own numbered responses to `COMPREHENSION.md`.

An organization such as `include/`, `src/`, and `tests/` is encouraged. Keep generated build products out of the submitted source tree or isolate them under `build/`.

## Test obligations

Tests must construct ASTs directly and assert behavior rather than merely print results for visual inspection. Cover at least:

- every statement and expression form;
- environment changes across compound statements;
- left-to-right operand and print-expression evaluation;
- a nested `Eseq` whose statement prints or assigns;
- prints nested inside expression trees for `max_print_arity`;
- the no-print result for `max_print_arity`;
- unbound-name, division-by-zero, and each arithmetic-overflow category;
- suppression of the failing print's partial line;
- preservation of effects completed before a later error; and
- repeat calls that show the analysis has no leaked mutable state.

Prefer small, named tests with one clear reason to fail. Tests should compare exact output bytes, result values, final environment state where applicable, and error categories. Avoid assertions that depend only on private implementation details.

## Reproducible workflow

The following sequence must work from the submission root with an available C++17 toolchain and CMake:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

You may also run compiler warnings or sanitizers if available, but the project must not require network access or optional local tools to pass its normal test workflow.

## Scope controls

Do not implement a lexer, parser, type checker, optimizer, code generator, LLVM integration, or an external framework adapter. Do not fetch the linked textbook, slides, website, old framework, or restricted current framework for this task. Standard-library-only code is sufficient.

## Submission self-check

Before handing off, confirm that a fresh build succeeds, CTest discovers and runs the tests, errors are asserted structurally, output comparisons include whitespace, documentation matches behavior, and only the requested unit is claimed. This self-check is not a passing decision; an independent validator makes that decision.

## Provenance

This task is a new, learner-safe specification based only on the catalog topic “Lab 1: Straight-line Program Interpreter.” The snapshot content hash is `c0b01a3547deab67a2c9ce70808ae093949cc577ef4b3208bb40f409922c4189`; no linked content was retrieved. `PREPARED_UNVALIDATED` means no learner implementation has yet been validated.
