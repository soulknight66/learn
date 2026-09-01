# Adversarial evaluation notes

After ordinary tests pass, probe sequences rather than isolated examples:

- tiny terminal geometries, guards on both sides, repeated scrolling, and control bytes at edges;
- prefix followed by unsupported input, independent left/right modifier release, Caps+Shift, and
  long streams containing `0xe0`/`0xe1`;
- queue fill, failed push, wraparound, partial drain/refill, and preservation of output on empty.

Do not add expectations or reference outputs here. The deterministic solution-bearing stress harness
is sealed. Passing it still does not validate privileged I/O or earn a fuzzing claim.
