# Sealed reference implementation

`src/minic.c` is an independently authored C11 reference implementation of the exact language in
`REQUIREMENTS.md`. It contains a lexer, recursive-descent compiler, symbolic call resolver,
bounded stack VM, checked arithmetic, source diagnostics, and deterministic instruction budget.

Build and run from the repository root:

```sh
make -C sealed/reference clean all
python3 sealed/reference_tests/run_tests.py sealed/reference/build/minic
sealed/reference/build/minic sealed/reference/examples/meta_vm.mc
```

The implementation intentionally uses fixed documented capacities after source/compiler
allocation. It is a teaching reference, not a hardened sandbox or ISO C implementation. See
`sealed/production/PRODUCTIONIZATION.md` before considering any use with untrusted input.
