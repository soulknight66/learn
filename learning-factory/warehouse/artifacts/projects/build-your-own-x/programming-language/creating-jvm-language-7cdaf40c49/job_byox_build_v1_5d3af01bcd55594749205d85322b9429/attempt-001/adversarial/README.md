# Adversarial corpus notes

These non-secret cases probe semantic distinctions that ordinary happy-path
examples miss. They are inputs, not expected-output answer keys.

- `cases/short_circuit.sprig` places division by zero behind both kinds of
  logical short circuit.
- `cases/path_visibility.sprig` uses a declaration on only one continuing path.
- `cases/crlf_location.sprig` is an invalid-character baseline; validators should
  materialize copies with LF, CR, and CRLF endings for location checks.
- `cases/overflow.sprig` distinguishes JVM wraparound from checked arithmetic.

Independent validation should also generate, rather than commit, boundary-size
programs for nesting, token, local-slot, branch-span, code-size, and constant-
pool limits. Run each in a process with bounded time and memory; a compiler hang,
host error, or malformed class is not an acceptable diagnostic.
