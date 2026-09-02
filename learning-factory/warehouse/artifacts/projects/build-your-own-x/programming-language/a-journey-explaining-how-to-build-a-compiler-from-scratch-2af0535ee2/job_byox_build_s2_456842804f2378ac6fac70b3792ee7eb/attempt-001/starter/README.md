# Starter workspace

The lexer, file-loading CLI, public header, and build are complete. `compiler.c` and `vm.c` contain intentional stubs that accept only an empty program. Work through the milestones in the root README; do not replace the command-line boundary or inspect sealed material.

Build and inspect what is already available:

```sh
make -C starter clean all
starter/build/sprig --tokens starter/examples/hello.sprig
python3 public_tests/run_tests.py --binary starter/build/sprig
```

The starter’s expected initial public-test result is a mixture of passes and failures. The test runner exits nonzero until the compiler and VM meet the contract.
