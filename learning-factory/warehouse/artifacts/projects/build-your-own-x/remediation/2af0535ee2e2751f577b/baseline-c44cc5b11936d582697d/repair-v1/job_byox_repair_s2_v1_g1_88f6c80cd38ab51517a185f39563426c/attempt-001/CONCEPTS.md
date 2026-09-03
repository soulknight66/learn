# Concepts map

## Lexing is controlled information loss

The lexer turns bytes into token kinds while retaining only the payload and source coordinates later stages need. Its one-token-at-a-time API keeps ownership simple in C. Notice the deliberate distinction between an integer’s spelling and unary minus: `-3` is parsed as two tokens, which makes precedence explicit.

## Recursive descent mirrors the grammar

One function per precedence level makes the call graph encode binding strength: `expression` calls `term`, which calls `unary`, which calls `primary`. Loops implement left-associative binary operators; recursion implements prefix negation and parentheses. The parser maintains one lookahead token and reports the unexpected token’s coordinates.

## Compilation resolves names early

Sprig assigns each declaration a numeric slot. A later identifier compiles to `LOAD slot`, so the VM never handles strings or scope rules. This is a small but real compiler transformation: syntax and names become a lower-level instruction sequence.

## A bytecode interpreter needs invariants

For each opcode, write down its stack effect. The compiler should never emit a sequence that underflows, but the VM must still validate arbitrary chunks defensively. Host C signed overflow is undefined, so checking bounds before arithmetic is part of the language semantics, not an optional hardening step.

## Language design appears in edge cases

Immutable single-assignment bindings avoid assignment semantics. Requiring declaration before use avoids a separate linking pass. Fixed limits make allocation and failure deterministic. Stable exit codes and source positions make the command-line compiler usable by other tools. Each simplification costs expressiveness but exposes a teachable boundary.

## Suggested milestones

1. Emit `CONST`, `PRINT`, and `HALT` for literal-only programs.
2. Add precedence and parentheses; inspect disassembly before running code.
3. Add `let`, symbol lookup, and deterministic declaration errors.
4. Implement VM stack effects and checked arithmetic.
5. Harden limits and diagnostics without changing successful output.
