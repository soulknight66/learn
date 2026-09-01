# Public tests

These are deterministic black-box tests written with Node's built-in `node:test`
runner. They import only the documented CommonJS entry point and communicate with
applications through real loopback HTTP requests. They do not inspect an
implementation's route stack or other internals.

Run every stage from the repository root:

```bash
node --test public_tests/*.test.js
```

The numbered files progress from API surface to middleware, routing, responses,
errors, and concurrent request isolation. Run one stage while developing, for
example:

```bash
node --test public_tests/02_middleware.test.js
```

The supplied starter is intentionally incomplete. Stage 01 is designed to pass;
later stages may fail until their features are implemented. Public tests are
examples, not an exhaustive substitute for `REQUIREMENTS.md`; additional
evaluation may cover other documented cases.

Each HTTP request has a three-second in-process timer and a 1 MiB response
limit. Those controls bound handlers that yield to the event loop; they cannot
interrupt a synchronous infinite loop or a microtask loop that starves timers.
Server startup and cleanup use the same kind of yielding-operation timer. For a
wall-clock boundary around the entire process, run:

```bash
python3 environment/run-bounded.py 30 -- node --test public_tests/*.test.js
```

That wrapper launches an argv array without a shell, captures at most 2 MiB of
combined output, and terminates the child's process group at the deadline. The
test suite needs no npm packages and does not contact the public network.
