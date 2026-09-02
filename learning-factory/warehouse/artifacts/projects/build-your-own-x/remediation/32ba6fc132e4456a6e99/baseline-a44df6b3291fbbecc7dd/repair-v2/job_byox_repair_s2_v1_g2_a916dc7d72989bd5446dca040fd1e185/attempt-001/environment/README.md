# Reproducible environment

The project requires Java 21 and Python 3 only for the convenience test runner.
It has no network, package-manager, database, or service dependency.

Validated toolchain locations for this generated artifact:

- Java home: `/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11`
- Python: `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`

`run_public_tests.py` invokes `javac` and `java` with argument arrays, captures
their output, applies 60-second timeouts, and compiles into an automatically
removed scratch directory. Each child starts in a new process group; a timeout
terminates that group, including descendants. Override `--java-home` to use
another Java 21 JDK.

The runner does not rely on Python's host-default temporary directory. By
default it tries `.minilog-runner-tmp` first in the repository and then in the
repository's parent, removing what it creates. Use
`--temp-root <writable-directory>` to choose the scratch parent explicitly.

No toolchain root is placed on `PATH`. See `VALIDATION.md` for exact observed
versions and results from artifact generation.

## Learner-view projection

`learner_view.json` is the exact top-level allowlist for learner-visible
material. `project_learner_view.py` rejects duplicate policy keys, missing
allowlisted inputs, symlinks, special files, existing destinations, and
source/destination nesting. It copies only the allowlist and verifies the
result against a SHA-256 inventory computed in memory.

A source-only policy check creates no learner workspace:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B environment/project_learner_view.py . --check-source
```

The acceptance harness, outside this production-builder workspace, can create
the actual isolated view by supplying a new destination:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B environment/project_learner_view.py EVALUATOR_PACK NEW_LEARNER_VIEW
```

Projection alone does not prove runtime isolation from its source. The harness
must mount or expose only the projected destination and independently verify
that the evaluator pack is unreadable before awarding `TRANSFER_VERIFIED`.
