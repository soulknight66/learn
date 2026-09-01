# Starter workspace

This module fixes the public API while leaving the seven core stages incomplete. It builds before you start: the small local tests check only permanent API invariants, never a temporary `NOT_IMPLEMENTED` result. Those tests therefore remain valid after each stage is completed. `public_tests/` holds behavioral tests that initially fail with `SCAN/NOT_IMPLEMENTED`.

Recommended milestones:

1. Implement `Scan`; run public tests whose names start with `TestScan`.
2. Implement `Parse`; inspect AST fields directly while testing spans.
3. Implement `Analyze`; test forward references, self-reference, and redeclaration.
4. Implement `Compile`; compare instruction sequences and stack effects.
5. Implement `ValidateBytecode` before `Run`.
6. Finish checked arithmetic, pipeline behavior, and command behavior.

You may split `compiler.go` into stage-specific files. Preserve declarations in `types.go` and `errors.go`, including numeric enum order. Do not use a parser generator or third-party module; the challenge is small enough to implement directly.

Run:

```bash
go test ./...
(cd ../public_tests && go test ./...)
go run ./cmd/pebble <<'EOF'
(let n 7)
(print (* n (+ n 1)))
EOF
```

The final command should print `56`. Consult `REQUIREMENTS.md` for edge cases; examples here are illustrative, not a replacement for the contract.
