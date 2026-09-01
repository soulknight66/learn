# Study Task: Build a Testable 2D Transform Pipeline

## Goal and boundary

Build a C++17 command-line program named `transform2d`. It reads a small transform description, composes the transforms in file order, and applies the result to named 2D points. The work should demonstrate both mathematical correctness and software-engineering discipline.

Do not add rendering, OpenGL, 3D transforms, general matrix inversion, a GUI, or third-party math/parser/test libraries. They are outside this 6–8 hour unit.

## Required project shape

Submit at least:

```text
CMakeLists.txt
README.md
DESIGN.md
include/          # public math declarations
src/              # math, parser, and CLI implementation
tests/            # learner-authored automated tests
COMPREHENSION_RESPONSES.md
```

You may refine filenames. Keep the mathematical core separate from parsing and process-level input/output; `main` must not contain the whole implementation.

Use only C++17 and its standard library. Store matrix values as `double`. Your build must create the `transform2d` executable and register automated tests with CTest.

## Mathematical contract

Use the column-vector convention in `COURSE_BRIEF.md`. Implement:

- a 3-by-3 identity matrix;
- translation `T(tx, ty)`;
- scaling `S(sx, sy)`;
- counterclockwise rotation `R(theta)` with `theta` in radians;
- matrix-by-matrix multiplication; and
- application of a matrix to a 2D point represented homogeneously with `w = 1`.

For operations `O1`, `O2`, ..., `Ok` encountered in that order, compute

```text
M = Ok * ... * O2 * O1
```

and output `M * p` for each point. Building the running composite by applying each operation separately to every point is not sufficient: the program must represent and test composition.

## Invocation and input contract

Invoke the program with exactly one path:

```bash
transform2d INPUT_FILE
```

The input is UTF-8 text whose recognized content is ASCII. Ignore blank lines. After optional leading whitespace, `#` begins a comment extending to end of line. Each remaining line is exactly one command:

```text
translate TX TY
scale SX SY
rotate RADIANS
point ID X Y
```

Rules:

1. Zero or more transform commands come first, followed by one or more point commands.
2. After the first `point`, any transform command is a syntax error.
3. `ID` matches `[A-Za-z_][A-Za-z0-9_-]{0,31}` and must be unique.
4. Each numeric token must consume the entire token, represent a finite `double`, and use `.` as the decimal point. Decimal exponent notation is allowed.
5. Unknown commands, wrong token counts, stray tokens, or an invalid ID are syntax errors.
6. Non-finite intermediate or final matrix/point values are range errors.

Collect and validate the entire file before writing result lines. This prevents a late error from leaving plausible partial output.

## Output and failure contract

On success, emit one line per point in original point order:

```text
ID X_RESULT Y_RESULT
```

Separate fields with one ASCII space. Print enough significant decimal digits to round-trip a `double` (for example, `std::numeric_limits<double>::max_digits10`). Convert an exact negative zero to positive zero before formatting. Write nothing to standard error and exit with status `0`.

On failure, write no standard output, write exactly one of these lines to standard error, and exit with status `2`:

```text
error: usage
error: io
error: syntax
error: number
error: duplicate-id
error: missing-point
error: range
```

Use `usage` when the argument count is wrong, `io` when the named file cannot be read, `number` when a required numeric token is not a finite `double`, `duplicate-id` for a repeated valid ID, `missing-point` when the parsed file contains no points, and `range` for non-finite arithmetic results. All other input-contract violations are `syntax`.

## Required test evidence

Write automated tests that exercise the public behavior and, where practical, the pure math interface. Your suite must include:

- identity and each elementary transform;
- at least two operations whose reversed order produces a different point;
- three or more operations composed together;
- more than one point, with output order checked;
- an inverse round-trip property over several fixed, finite cases with nonzero scales;
- decimal exponent input and boundary-valid IDs;
- every failure category above;
- rejection of an operation after the point section starts;
- duplicate detection before any output is emitted; and
- a numeric comparison helper with a documented absolute/relative tolerance.

Tests must fail when a checked behavior is deliberately broken. Do not use current time or an unfixed random seed.

## Documentation and build evidence

In `README.md`, give the exact fresh-build workflow:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

Also show one invocation using a small input file, but do not paste generated build products into the submission.

In `DESIGN.md`, document:

- the vector/matrix convention and composition invariant;
- module responsibilities and how errors cross their boundaries;
- why the program buffers results until validation succeeds;
- the floating-point comparison policy used by tests;
- time and auxiliary-space complexity in terms of transform count `t` and point count `p`;
- one design tradeoff or rejected alternative; and
- a test inventory that distinguishes direct examples, properties, and error cases.

Answer every prompt from `COMPREHENSION.md` in `COMPREHENSION_RESPONSES.md` in your own words.

## Completion checklist

Before handing off, use a new build directory and confirm that configuration, compilation, and CTest all succeed. Confirm that your repository contains sources and documentation rather than generated binaries or build trees. A handoff claim is not proof: preserve the rerunnable commands and artifacts so an independent validator can examine them.
