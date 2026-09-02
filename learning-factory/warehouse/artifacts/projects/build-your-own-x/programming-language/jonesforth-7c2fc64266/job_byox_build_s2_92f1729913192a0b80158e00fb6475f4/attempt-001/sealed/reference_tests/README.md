# Sealed reference tests

`test_reference.py` checks signed edges, wrapping behavior, all division sign combinations, fixed
capacity boundaries, dictionary naming, exact code-arena fill, malformed branch nesting, recursion
depth, input length, comments, and compile-only words. Tests use an argv array, captured streams, and
a five-second timeout.

After building the reference, run from the root:

```text
REFERENCE_BIN=sealed/reference/build/cinder-reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```
