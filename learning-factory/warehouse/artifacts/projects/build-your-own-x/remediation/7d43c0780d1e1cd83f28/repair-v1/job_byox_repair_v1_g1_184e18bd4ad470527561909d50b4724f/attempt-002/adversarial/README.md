# Adversarial contract harness

This directory contains instructor-side black-box checks for the mini web
framework. The harness uses only Node.js built-ins and sends requests over an
ephemeral loopback server. It does not inspect application internals.

Run it from the repository root:

```bash
node adversarial/run.js
```

The default target is `sealed/reference/src/index.js`. To check another
CommonJS implementation, pass its module path:

```bash
node adversarial/run.js starter/src/index.js
```

The module must export `createApplication` directly. Each request has a two-second
in-process timer and a 1 MiB response cap; server shutdown has a one-second
timer. These timers require the event loop to yield. Use an outer process-group
deadline for untrusted targets:

```bash
python3 environment/run-bounded.py 30 -- node adversarial/run.js starter/src/index.js
```

Tests run serially except for the explicit isolation case. The harness covers
dispatch ordering, mount boundaries, decoded parameters,
duplicate query keys, wildcard capture, error flow, repeated `next`, HEAD
selection, malformed encodings, concurrent request isolation, and the default
404 response.

This is supplementary evidence, not an independent validation label. Exact
expected outcomes and the rationale for the cases are kept in
`sealed/exercises/ADVERSARIAL_EXPECTATIONS.md`.
