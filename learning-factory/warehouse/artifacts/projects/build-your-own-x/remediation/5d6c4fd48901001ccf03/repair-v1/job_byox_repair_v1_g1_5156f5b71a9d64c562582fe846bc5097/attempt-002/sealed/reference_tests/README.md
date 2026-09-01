# Reference tests

This directory contains implementation-specific self-tests for the bundled
reference and production packaging controls. It is intentionally kept under
`sealed/`; do not copy it into a learner view. The suite uses temporary files
and fake execution backends. It does not execute a real namespace plan.

Run the reference implementation and all reference tests from the repository root:

```bash
PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -v
```

This command is **not** a learner-conformance command. Several tests deliberately
assert private reference CLI/helper protocols and packaging internals that are
outside the normative learner contract. Do not point this suite at `starter/`
and do not grade learner implementations with it. Learner validation is limited
to requirements-derived tests; the visible suite is `public_tests/`.
