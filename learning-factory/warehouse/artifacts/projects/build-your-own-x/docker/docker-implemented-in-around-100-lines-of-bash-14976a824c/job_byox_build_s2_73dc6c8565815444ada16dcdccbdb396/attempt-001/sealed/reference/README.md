# Sealed reference implementation

This directory contains one independent reference solution. It is sealed because its controller,
namespace runner, and operational notes directly answer the learner exercise.

`tinybox.sh` implements the deterministic controller contract. `runner.sh` uses a two-stage
invocation: the outer stage asks `unshare` for namespaces, and the inner stage uses host tools before
changing root and executing the requested argv. This avoids constructing a shell command string.

Run the deterministic reference tests from the repository root:

```bash
bash sealed/reference_tests/test_reference.sh
```

Passing those tests does not certify the Linux backend. The actual namespace probe is separately
reported in `VALIDATION.md`.
