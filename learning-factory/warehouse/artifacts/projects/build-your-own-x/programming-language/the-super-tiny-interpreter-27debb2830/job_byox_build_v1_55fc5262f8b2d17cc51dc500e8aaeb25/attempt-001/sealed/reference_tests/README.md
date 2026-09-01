# Sealed reference tests

These evaluator-only tests exercise the independent reference pipeline, negative behavior, resource
limits, and tree/VM agreement. They require Node.js 20 or newer and no installed dependencies.

The generator could not run them because no compatible Node.js runtime was present. Their existence is not a
validation label; see `../../VALIDATION.md`.

A supplemental `gjs_bundle.py` mechanically removes module syntax and downlevels a small set of
modern expressions so the core algorithms can receive smoke coverage on the host's legacy GJS. That
check does not validate the original ESM syntax, Node integration, or the `node:test` assertions.
