# Public contract tests

This directory contains a framework-free Java 17 contract suite for the public
starter API. It uses a small built-in test harness, so it downloads no libraries
and requires no build tool.

From the repository root, run:

```sh
sh public_tests/run.sh
```

The script compiles the starter sources and public tests into a temporary
directory, executes the tests, and removes the temporary classes on exit. A
successful run prints the number of passed contract cases.

The public cases cover core API behavior, but they are not exhaustive.
`REQUIREMENTS.md` remains the authoritative learner-visible contract.
