# Starter package

`sprig/` fixes the module boundaries and public interfaces while leaving the language logic as
milestone-marked tasks. Work in this directory only.

Suggested order:

1. `values.py`, then tokenization/parsing in `reader.py`
2. environments and builtins in `runtime.py`
3. special forms/calls/budgets in `evaluator.py`
4. instruction generation in `compiler.py` and execution in `vm.py`
5. error translation and modes in `cli.py`

Run each numbered public test module as it becomes relevant. `NotImplementedError` from the starter is
intentional, but it should not remain in a completed solution.
