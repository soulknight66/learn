# Starter implementation

The supplied C11 program completely implements bounded source loading,
tokenization, token positions, comments, keyword recognition, integer-range
checks, and `mica tokens`. It builds without warnings. The parser, validator,
interpreter, and native backend are deliberately replaced by one explicit
unfinished-stage diagnostic.

Build and inspect the example:

```bash
make -C starter clean all
starter/mica tokens starter/examples/countdown.mica
starter/mica run starter/examples/countdown.mica
```

The second command initially exits 3. Replace `unfinished_pipeline` in
`src/mica.c` as you complete the stages; splitting the file into modules is
encouraged. Do not change token kind names because they are part of the public
CLI contract.

Suggested checkpoints:

1. Parse integer-only `print` statements.
2. Add unary and binary expressions one precedence level at a time.
3. Add declarations, assignment, and validation.
4. Add blocks and interpreted control flow.
5. Emit straight-line assembly, then labels and branches.
6. Differentially compare `run` with linked native output.
