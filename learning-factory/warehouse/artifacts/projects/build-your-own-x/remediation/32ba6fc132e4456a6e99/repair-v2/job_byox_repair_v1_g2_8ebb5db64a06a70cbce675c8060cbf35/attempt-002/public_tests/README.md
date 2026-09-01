# Public contract tests

This directory contains a framework-free Java 17 contract suite for the public
starter API. It uses a small built-in test harness, so it downloads no libraries
and requires no build tool.

From the repository root, run:

```sh
sh public_tests/run.sh
```

The default runs all twelve cases. During implementation, select exactly one independent group:

```sh
sh public_tests/run.sh milestone-1  # records and a local partition log: 4 cases
sh public_tests/run.sh milestone-2  # replication and commit visibility: 2 cases
sh public_tests/run.sh milestone-3  # quorum loss and elections: 3 cases
sh public_tests/run.sh milestone-4  # replica recovery: 3 cases
```

An unknown selector exits with status 2 and prints the accepted values. A selected group does not
invoke earlier or later groups, so an unfinished later milestone cannot obscure the current result.

The script compiles the starter sources and public tests into a temporary
directory, executes the tests, and removes the temporary classes on exit. A
successful run prints the number of passed contract cases.

The public cases cover core API behavior, but they are not exhaustive.
`REQUIREMENTS.md` remains the authoritative learner-visible contract.
