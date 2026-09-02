# Sealed harness tests

This evaluator-only Python `unittest` suite checks scratch-directory fallback,
verifies that timeout cleanup kills a SIGTERM-ignoring descendant in the
command's process group, and tests learner-view allowlisting. The projection
case uses synthetic fixture data only; it never copies this pack or its sealed
implementation into a learner workspace.

Run it from the repository root without writing bytecode into the pack:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B -m unittest discover -s sealed/harness_tests -v
```
