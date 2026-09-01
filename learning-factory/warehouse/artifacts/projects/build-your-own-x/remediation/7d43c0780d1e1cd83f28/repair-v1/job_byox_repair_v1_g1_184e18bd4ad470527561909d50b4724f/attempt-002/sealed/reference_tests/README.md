# Reference test suite

The suite requires Node.js 18.17 or newer and has no installation step or third-party dependencies.
Every HTTP assertion uses an ephemeral loopback server. Requests have a three-second in-process
timer and a one-megabyte response limit, and the concurrency case uses an explicit arrival barrier
rather than assuming timer ordering. The timer requires the event loop to yield; use the pack's
process-group wrapper when evaluating untrusted code that may loop synchronously.

Run the complete suite from the repository root with exactly:

```bash
node --test sealed/reference_tests/*.test.js
```

For a 30-second outer wall-clock boundary with 2 MiB of captured output:

```bash
python3 environment/run-bounded.py 30 -- node --test sealed/reference_tests/*.test.js
```

The shell expands the glob to the three `*.test.js` files; `helpers.js` is imported by those tests
and is not itself a test entry point.
