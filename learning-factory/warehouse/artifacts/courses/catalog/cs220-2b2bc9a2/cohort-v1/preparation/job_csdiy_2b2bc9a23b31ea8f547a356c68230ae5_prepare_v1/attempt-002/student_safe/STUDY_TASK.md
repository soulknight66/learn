# Study Task: Deterministic Dependency Planner

## Goal and time box

Build a small Rust library and CLI that convert a text dependency description into a deterministic topological plan. Target **six hours** and stop after the bounded deliverables below; this is the first practice unit, not a request to reconstruct the full CS220 course.

Use stable Rust and the standard library only. Do not fetch code, tests, or assignment content from the linked course resources for this task.

## Required project files

Create a Cargo package named `dependency_planner` containing:

- `Cargo.toml`;
- `src/lib.rs` for the input contract and planning logic;
- `src/main.rs` for standard-input, standard-output, and exit-status handling;
- your unit and integration tests in normal Cargo locations;
- `README.md` with the input contract, command usage, and two original examples;
- `REFLECTION.md` with 250–400 words addressing the prompts below.

Do not add third-party dependencies. Do not commit generated build output.

## Library contract

Expose this public entry point:

```rust
pub fn plan(input: &str) -> Result<Vec<String>, PlanError>
```

Expose a public `PlanError` enum that derives `Debug`, `PartialEq`, and `Eq` and can distinguish:

- an invalid input line, including its one-based line number and a useful diagnostic; and
- a cycle, including a lexicographically sorted list of every task left unscheduled.

The precise internal representation is your choice. Keep parsing and graph traversal as separately testable responsibilities, even if their helpers remain private.

## Input language

Interpret UTF-8 input one line at a time:

1. Trim leading and trailing whitespace.
2. Ignore an empty line or a line whose first non-whitespace character is `#`.
3. A line containing no `->` declares one task.
4. A line containing exactly one literal `->` declares that the task on the left must run before the task on the right.
5. After trimming, every task identifier must match `[A-Za-z][A-Za-z0-9_-]*`.
6. An empty endpoint, invalid identifier, or line with more than one `->` is invalid input.
7. Repeated task declarations and repeated identical edges are idempotent.

Do not panic on user input. Return the first invalid-line error encountered.

## Planning behavior

For valid acyclic input, return every declared or referenced task exactly once in a valid topological order. Whenever several tasks are ready, choose the lexicographically smallest identifier. This tie rule is part of the contract; output must not depend on hash iteration order.

For cyclic input, return the cycle variant with all unscheduled tasks sorted lexicographically. “Unscheduled” includes tasks blocked downstream of a cycle, whether or not they are themselves members of a cycle.

The empty input is valid and produces an empty plan.

## CLI behavior

The binary reads the complete graph description from standard input.

- On success, print each planned task on its own line and exit successfully. An empty plan prints nothing.
- On invalid input or a cycle, print a concise diagnostic to standard error, print no plan to standard output, and exit with status `2`.

Keep process I/O in the binary and reusable behavior in the library.

## Test obligations

Write focused tests that cover at least:

- empty input and a single declared task;
- a chain and a graph with multiple simultaneously ready tasks;
- declarations mixed with edges, comments, and surrounding whitespace;
- duplicate declarations and duplicate edges;
- each invalid-line category and correct one-based line reporting;
- a self-loop, a multi-task cycle, and a task blocked downstream of a cycle;
- repeated runs yielding the same order;
- CLI success and CLI failure, including output-stream separation and exit status.

Choose small fixtures whose intent is clear from the test name. Add any boundary tests you discover while implementing.

## Suggested work sequence

1. Create the package and make an empty plan work through both the library and CLI.
2. Define the public error type and implement line parsing with focused tests.
3. Implement deterministic planning and cycle reporting.
4. Add CLI-level tests, review ownership and cloning, and finish the documentation.
5. Run the full local quality loop and record any unresolved limitation honestly.

Use these commands from the package root:

```text
cargo fmt --check
cargo build --locked
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
```

If a required tool is unavailable in your environment, record the exact command and observed limitation; do not report an unrun check as passing.

## Reflection prompts

In `REFLECTION.md`, explain:

1. where your program borrows data and where it creates owned data, including one clone you retained or removed;
2. how your data structures enforce deterministic tie-breaking;
3. one failure you represented as data instead of a panic and why;
4. one test that changed or clarified your design;
5. any substantive human or tool assistance used, or state that there was none, plus how you verified suggestions.

After the implementation, respond to the separate prompts in `COMPREHENSION.md` in a file named `COMPREHENSION_RESPONSE.md`. Use your own reasoning and refer to your implementation where requested.

Submitting files is not itself proof of completion. A worker-harness-controlled validator determines whether this kickoff unit passes, and a pass applies only to this unit.
