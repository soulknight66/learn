# Starter module

This directory is the only implementation area learners should modify. It
already fixes the public data model, opcodes, resource limits, stable bytecode
format, CLI shell, and pipeline wiring. Core stages in `pipeline.go` deliberately
return `ErrNotImplemented`.

Suggested milestones:

1. Split `pipeline.go` into lexer and parser implementations; make lexer/parser
   public tests pass first.
2. Add a non-emitting type-check pass.
3. Emit bytecode while computing its true maximum operand-stack height.
4. Implement the defensive VM, then the independent AST evaluator.
5. Exercise the same programs through `Execute`, `Evaluate`, and the CLI.

Keep exported names compatible. You may add unexported files, helpers, and tests.
The initial module should compile even though behavioral public tests fail:

```bash
go test ./...
```
