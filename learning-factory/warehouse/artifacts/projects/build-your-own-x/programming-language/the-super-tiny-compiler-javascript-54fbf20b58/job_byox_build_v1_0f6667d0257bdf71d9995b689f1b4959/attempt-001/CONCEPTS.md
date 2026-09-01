# Concepts behind Pebble

## Lexing is lossless boundary detection

A tokenizer decides where syntax starts and ends before the parser knows what the tokens mean.
Keeping exact lexemes and source locations makes later diagnostics possible. Multi-character
operators require deliberate lookahead, and comment handling demonstrates why `/` cannot be handled
without context. EOF is a real token because it gives incomplete constructs a location.

## Precedence is encoded in parser structure

The grammar gives each precedence level its own rule. A recursive-descent parser can mirror those
levels directly; a Pratt parser can express the same table as binding powers. Either approach must
also decide associativity. Pebble's binary operators associate left, while unary operators nest from
the right.

An AST intentionally discards punctuation that no longer matters. Parentheses change tree shape but
do not need their own runtime node. In contrast, blocks remain nodes because control-flow statements
need ordered statement lists.

## An interpreter defines meaning

The tree evaluator is the clearest executable semantics for the language. Its environment maps
names to typed Pebble values, and its output array represents the only observable side effect. Type
checks belong at operator boundaries so JavaScript coercion never accidentally becomes a language
feature.

Evaluation order matters even in a tiny language. Establishing it now prevents a future side effect
or error from behaving differently after compilation.

## Compilation turns structure into control flow

An AST keeps branches nested; bytecode must flatten them into instructions and explicit branch
destinations. Those destinations depend on the amount of code produced for each nested construct.
There are several valid strategies—single-pass fixups, multiple passes, labels, and intermediate
basic blocks—and choosing among them is part of the design work.

A stack target makes individual instruction effects local, but nested expressions and control-flow
merges still have to agree about stack height. Defining an invariant for expressions, statements,
and branch joins is part of the compiler design and gives both tests and validators something
precise to check.

## A virtual machine is an untrusted-data boundary

The VM should not assume that all bytecode came from your compiler. It must account for object
shapes, opcode arguments, jumps, stack effects, termination structure, and work limits. Which checks
belong in a separate validation phase and which belong in dispatch is a design choice; malformed
programs must become Pebble errors rather than hangs or host-language crashes.

## Differential testing is a practical oracle

The evaluator and VM implement the same semantics through different mechanisms. Generate or hand
write valid programs, run both backends, and compare outputs and error categories. Agreement is not
proof—both implementations can share a bug—but disagreement immediately identifies a defect.

Useful tests vary precedence, nested branches, zero-iteration loops, mutations across blocks,
comments at EOF, and failures in code that must not execute. Metamorphic properties, such as adding
redundant parentheses without changing output, broaden coverage without hard-coding every result.

## Language design means choosing what not to support

Pebble omits strings, functions, lexical scopes, implicit coercion, and short-circuit operators.
Those omissions keep the semantic surface small enough to specify fully. Each extension would touch
multiple phases: grammar, AST, evaluator, compiler, VM, errors, and tests. Thinking through that
cross-cutting impact is part of the exercise.
