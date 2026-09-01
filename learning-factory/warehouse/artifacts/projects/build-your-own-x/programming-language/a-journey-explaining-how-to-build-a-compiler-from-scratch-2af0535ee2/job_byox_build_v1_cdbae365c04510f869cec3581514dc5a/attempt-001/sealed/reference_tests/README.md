# Sealed reference tests

These tests supplement the public black-box suite with integer boundaries, lexical edge cases, scope
lifetime, repeat execution, compile-failure atomicity, and caller-controlled limits. They are evidence
for the included reference implementation only; evaluators should still test learner implementations
independently and should not reveal these cases as solution hints.

Run make -C sealed/reference test to build and execute both the Python CLI suite and the C API harness.
