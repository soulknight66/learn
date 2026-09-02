# Sealed harness tests

This evaluator-only Python `unittest` suite checks scratch-directory fallback
for an immutable repository and verifies that timeout cleanup kills a
SIGTERM-ignoring descendant in the command's process group.

Run it from the repository root without writing bytecode into the pack:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -m unittest discover -s sealed/harness_tests -v
```
