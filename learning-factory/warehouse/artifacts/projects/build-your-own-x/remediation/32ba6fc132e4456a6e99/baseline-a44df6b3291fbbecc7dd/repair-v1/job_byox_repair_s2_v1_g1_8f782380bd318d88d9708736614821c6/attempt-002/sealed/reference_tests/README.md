# Sealed reference tests

These evaluator-only tests supplement the public suite with corruption,
recovery, bounds, fencing, monotonicity, and resource-lifecycle cases. They use
a plain `main` method so validation needs no downloaded test framework.

`sealed/run_reference_tests.py` compiles the sealed reference together with
both suites in an automatically removed scratch directory, then runs the
public suite followed by 15 sealed cases. `--temp-root` selects an explicit
writable scratch parent. `sealed/harness_tests/` is a separate Python
`unittest` regression for timeout cleanup. Passing here is generation-time
evidence only; independent validation remains required.
