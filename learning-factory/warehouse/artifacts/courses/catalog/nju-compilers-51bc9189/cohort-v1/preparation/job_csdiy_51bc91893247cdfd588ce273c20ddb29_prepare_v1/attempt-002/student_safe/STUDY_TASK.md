# Study Task: Build a Tiny Expression Front End

> Artifact classification: learner-safe task specification  
> Validation label: prepared task; completion requires independent execution and review  
> Provenance: course-manager-authored from the supplied CSDIY catalog metadata; no official assignment text was used

## Goal

Build a small Java command-line application with ANTLR 4. Given one source file, it must parse exactly one expression and print a deterministic parenthesized AST representation. The project must support a clean, repeatable build and an automated test run without an IDE.

Keep the work bounded to 8–10 focused hours. If an optional improvement threatens that limit, record it as future work instead of expanding the language.

## Language contract

The input consists of one nonempty expression followed by end-of-file.

- Integer literals are one or more ASCII decimal digits. Preserve their source spelling in output.
- Identifiers begin with an ASCII letter or underscore and continue with ASCII letters, digits, or underscores. Preserve their spelling.
- Operators are binary `+`, `-`, `*`, and `/`, plus prefix unary `-`.
- Parentheses may group an expression.
- Spaces, tabs, carriage returns, and line feeds separate tokens and are otherwise ignored.
- Prefix unary `-` binds tighter than `*` and `/`.
- `*` and `/` bind tighter than `+` and binary `-`.
- Binary operators at the same precedence level associate left.
- Parentheses override those rules.
- Any other character is a lexical error. Empty input, incomplete expressions, unmatched parentheses, and extra trailing tokens are invalid.

For valid input, print exactly one line to standard output using this representation:

- an integer or identifier is printed as its original token text;
- prefix negation is `(- child)`;
- a binary expression is `(operator left right)`; and
- grouping parentheses do not appear as separate AST nodes.

Do not evaluate expressions. For invalid input, print no AST, return a nonzero exit status, and write one stable diagnostic to standard error. The diagnostic must contain `LEXICAL` or `SYNTAX` as appropriate and a one-based line and column. Do not rely on ANTLR's default console messages as the application interface.

## Command and build contract

Choose Maven or Gradle and commit its normal project metadata. Pin the ANTLR tool/plugin and runtime to compatible explicit versions. Generated sources must be produced by the build in its build-output directory; do not hand-edit them or mix them into the authored source tree.

The root `README.md` must document, for a clean checkout:

1. the supported JDK version;
2. one noninteractive command that builds and runs all tests;
3. one noninteractive command that runs the application on a named UTF-8 input file; and
4. where generated sources and disposable build output appear.

Commands must return meaningful exit codes. A second clean build and test run should not depend on files left by the first run.

## Required deliverables

Place these in the learner submission:

- one or more `.g4` grammar files;
- authored Java code that invokes the generated parser, constructs or renders the specified AST shape, and controls diagnostics;
- pinned Maven or Gradle build metadata;
- automated tests;
- a root `README.md` containing the command contract; and
- `DESIGN.md`, limited to about 600 words, describing source/generated-code boundaries, the precedence strategy, error handling, and one deliberately deferred extension.

Write responses to `COMPREHENSION.md` in `RESPONSES.md`. Refer to relevant grammar rules, Java types, and test names. Do not paste generated parser code into the design note or responses.

## Test obligations

Build a compact suite that covers all of the following:

- every operator and both uses of `-`;
- precedence between additive, multiplicative, and unary operators;
- left associativity and parenthesized regrouping;
- identifiers, multi-digit integers, and mixed whitespace;
- invalid characters;
- empty input, a missing operand, unmatched parentheses, and valid-prefix-plus-trailing-input cases;
- the distinction between lexical and syntax failures;
- exit status and separation of standard output from standard error; and
- deterministic output when the same valid file is processed repeatedly.

Name tests by behavior so a reviewer can see which contract clause each test protects. Tests must assert results rather than merely print them.

## Suggested work order

Start by translating the contract into a small set of executable examples. Establish a clean build with pinned versions, then add the grammar and the thinnest Java entry point. Add AST rendering and controlled diagnostics, grow the boundary tests, and finish by running the documented commands from a clean workspace. Use the design note to explain decisions already demonstrated by the repository.

Stop when this vertical slice satisfies its contract. Do not add variables, evaluation, types, functions, statements, or code generation in this unit.
