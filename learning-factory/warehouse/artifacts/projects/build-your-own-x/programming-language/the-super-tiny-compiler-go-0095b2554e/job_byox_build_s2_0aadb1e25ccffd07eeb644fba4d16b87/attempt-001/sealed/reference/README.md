# Sealed reference implementation

This module is an independently authored implementation of the public Prefix
Forge contract. It contains a byte-positioned lexer, bounded recursive parser,
static checker, stack compiler with forward-jump patching, bytecode verifier,
VM, direct AST evaluator, and CLI.

It has no dependencies outside the Go standard library. When a Go toolchain is
available, use:

```bash
go test ./...
go run ./cmd/prefixc -mode=run '(print "ready") (add 20 22)'
```

The larger sealed test module is `../reference_tests`. This implementation is
reference material for an independent validator; its presence and prose are not
evidence that it builds on the current host.
