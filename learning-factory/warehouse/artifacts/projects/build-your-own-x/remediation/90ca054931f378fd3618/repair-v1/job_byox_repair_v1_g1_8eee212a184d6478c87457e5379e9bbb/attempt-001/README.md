# Build a Mini-C interpreter that can host an interpreter

Build a deterministic interpreter for a compact, explicitly specified C-like language. The
project starts with source loading and diagnostics, proceeds through lexing and precedence
parsing, compiles to bytecode, executes functions in a bounded virtual machine, and ends with
a staged self-interpretation demonstration.

The last milestone runs a stack-machine interpreter written in Mini-C on your Mini-C runtime.
That guest interpreter evaluates a second program and prints `42`. This is an honest,
reproducible bootstrap boundary: an interpreter is interpreting another interpreter written in
its own accepted language. It is not a claim that this subset accepts its complete C
implementation or arbitrary ISO C.

## Start here

1. Read `REQUIREMENTS.md` for the normative grammar, behavior, limits, and exit codes.
2. Review `CONCEPTS.md`, then answer `DESIGN_QUESTIONS.md` before opening implementation work.
3. Build the scaffold with `make -C starter`.
4. Implement the milestones listed in `starter/README.md`.
5. Run `python3 public_tests/run_tests.py starter/build/minic` after each milestone.

The public suite is intentionally incomplete. It includes smoke behavior and CLI validation, but
most boundary cases, malformed programs, resource limits, recursion, and the staged bootstrap still
require your own tests. Reference material is sealed for independent validation.

## Repository map

- `starter/`: buildable scaffold with marked implementation seams
- `public_tests/`: black-box smoke tests and fixtures
- `environment/`: supported tools and reproducibility commands
- `sealed/`: reference implementation, deeper tests, design record, and review answers
- `VALIDATION.md`: commands actually run on this generated artifact

Status remains `GENERATED` + `PARTIAL`. It has not been independently promoted to BUILDS,
TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED.
