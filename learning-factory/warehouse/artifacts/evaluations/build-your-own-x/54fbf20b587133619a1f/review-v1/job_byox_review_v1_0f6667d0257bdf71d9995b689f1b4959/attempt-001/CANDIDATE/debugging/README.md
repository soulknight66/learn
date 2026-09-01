# Debugging stage

These exercises isolate three failure modes in a small language toolchain. They
are ordered from a local scanner defect to a cross-component bytecode defect.
Each prompt contains enough evidence to investigate, but not the corrected code
or answer key.

1. [Exercise 01: scanner progress](exercise-01/README.md)
2. [Exercise 02: binary associativity](exercise-02/README.md)
3. [Exercise 03: jump patching](exercise-03/README.md)

For each exercise, write down the violated invariant before changing code. Then
add the smallest regression test that fails for the buggy version and passes
for the repair. Check whether the same invariant appears elsewhere in the
pipeline rather than treating the first symptom as the whole problem.
