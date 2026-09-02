# Concepts

## A pipeline is a set of contracts

A compiler is easier to reason about when each phase narrows uncertainty. Scanning turns characters into located tokens. Parsing turns token order into tree structure. Semantic analysis connects names to declarations and rejects programs whose syntax is valid but meaning is not. Optimization rewrites a valid tree. Generation lowers that tree to another language.

Keep the intermediate representations inspectable. When a test fails, you should be able to ask whether the wrong token, tree edge, binding, rewrite, or output fragment first appeared.

## Precedence without backtracking

Ripple's expression grammar has one function per precedence level. Each binary level parses its tighter child first and then consumes a repeated operator/right-hand pair. This naturally makes the listed binary operators left-associative. Unary parsing recurses at its own level, which makes `!!x` and `--x` possible without a special case.

## Syntax is not meaning

`emit missing;` has a perfectly valid shape, but `missing` has no declaration. Keeping that check out of the parser makes both phases simpler. The analyzer can also allocate opaque binding IDs. Those IDs let code generation avoid treating an untrusted Ripple name as JavaScript source text.

## Interpretation and compilation are an oracle pair

The tree-walking interpreter and generated JavaScript implement the same language through different mechanisms. Comparing their output over many generated programs is a strong way to find precedence, escaping, and optimizer mistakes. Agreement is useful evidence, but two implementations can share the same bug, so targeted specification tests still matter.

## Diagnostics are output

Location accounting and stable error codes are part of the language interface. Save the start location before scanning a token. At each loop, either advance the input or throw. At parser boundaries, report what construct was expected rather than leaking an accidental JavaScript exception.

## Safe lowering

Source identifiers and strings are attacker-controlled. A compiler should never concatenate them into executable positions without a controlled encoding. Ripple uses generated binding names and a closed built-in mapping. JSON string encoding is a convenient, testable way to emit primitive string literals.
