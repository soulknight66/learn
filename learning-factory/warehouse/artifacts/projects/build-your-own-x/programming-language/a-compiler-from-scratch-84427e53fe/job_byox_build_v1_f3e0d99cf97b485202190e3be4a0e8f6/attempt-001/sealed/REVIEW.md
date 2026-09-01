# Sealed implementation review

## What is strong

- The pipeline has explicit boundaries and deterministic representations.
- Longest-match lexing, source positions, precedence, declaration timing, lexical shadowing, and jump patching are directly tested.
- The VM validates every instruction's opcode, arity, constant domain, local index, and jump target before running.
- Runtime checks reject truthiness, Ruby-specific negative modulo behavior, overflow, stack underflow, uninitialized locals, bad output objects, and unbounded loops.
- The CLI uses no dynamic evaluation, subprocess, network, or third-party dependency.

## Findings before any production use

1. **High: recursive parser depth is unbounded.** Repeated unary operators or parentheses can exhaust the Ruby stack. Add an explicit nesting limit or an iterative parser strategy.
2. **High: source, token, AST, instruction, stack, and output sizes have no independent limits.** The step budget bounds executed instructions but not compilation memory or bytes written per embedding policy.
3. **Medium: bytecode verification is shape-based, not control-flow/data-flow based.** It does not prove stack height/type consistency at merge points or reject all unreachable malformed stack behavior.
4. **Medium: `Program` and nested instructions are mutable.** The VM snapshots instructions after validation, but callers can mutate compiler results and there is no integrity digest or serialized format.
5. **Medium: runtime errors lack source spans.** They identify the operation but cannot map back to source.
6. **Low: `Lexer#scan_tokens` is designed for one call.** Reusing the same lexer instance appends another EOF rather than returning an immutable cached result or rejecting reuse.
7. **Low: compiler and VM instances are stateful and not safe for concurrent calls.** Document single-use/confinement or refactor stage state into call-local objects.

The implementation is suitable as a reference for this bounded educational exercise only. No review label beyond generated internal review should be inferred; independent review is still required.
