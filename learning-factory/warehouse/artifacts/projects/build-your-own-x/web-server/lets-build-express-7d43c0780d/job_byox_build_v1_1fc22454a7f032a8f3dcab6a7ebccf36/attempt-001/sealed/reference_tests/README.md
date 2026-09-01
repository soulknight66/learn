# Reference test suite

The suite requires Node.js 18.17 or newer and has no installation step or third-party dependencies.
Every HTTP assertion uses an ephemeral loopback server. Requests have an absolute three-second
deadline and a one-megabyte response limit, and the concurrency case uses an explicit arrival
barrier rather than assuming timer ordering.

Run the complete suite from the repository root with exactly:

```bash
node --test sealed/reference_tests/*.test.js
```

The shell expands the glob to the three `*.test.js` files; `helpers.js` is imported by those tests
and is not itself a test entry point.
