# Concepts

## Lexer boundaries

A lexer converts bytes into tokens while retaining enough location data for useful diagnostics.
The difficult cases are boundaries: `!` versus `!=`, comment termination, identifiers that share
keyword prefixes, and integer overflow while accumulating digits. Rejecting early is safer than
letting a wrapped literal reach runtime.

## Recursive-descent precedence

One parser function per precedence level encodes binding power directly. Each level consumes a
left operand and folds repeated operators of its own rank. A run of unary prefixes can be collected
iteratively and applied in reverse, so `!-x` nests correctly without consuming one host stack frame
per prefix. Keeping assignment out of the expression grammar makes name stores and their side
effects unambiguous in this smaller language.

Recursive descent also needs a language-level nesting budget. Checking it before descending turns
adversarially deep but otherwise small source into a deterministic source diagnostic instead of a
host stack overflow. Exact-limit and one-over-limit cases should be black-box tests.

## Parse-to-bytecode compilation

Direct evaluation of an AST is approachable, but bytecode makes control flow, step accounting,
and function frames explicit. `if` and `while` become conditional and unconditional jumps. A
forward call is emitted with an unresolved symbolic target and patched only after every function
definition is known.

## Virtual-machine invariants

At every instruction boundary, the instruction pointer names valid bytecode, the operand stack is
within its capacity, and each frame owns a fixed local array. A call consumes its arguments in a
defined order, records a return address and stack base, then transfers control. A return restores
that base before publishing one result. Checking these invariants turns malformed internal state
into a deterministic failure instead of undefined host behavior.

## Checked arithmetic

Host-language signed overflow is undefined in C, so “compute and check afterward” is not enough.
Use bounds tests or checked compiler builtins before committing a result. Division has two special
faults: zero divisor and `INT64_MIN / -1`. The same exceptional pair matters for remainder.

## Language design as constraint design

Omitted features are part of the language design. Removing pointers, heap allocation, strings,
and global mutation makes execution easier to bound and isolate. Forbidding local shadowing keeps
slot resolution deterministic. These choices trade C compatibility for a smaller semantic surface
that can be implemented and tested thoroughly.

## Staged self-interpretation

Bootstrapping has levels. This project does not claim that the host's C source belongs to Mini-C.
Instead, the host runs an interpreter written in Mini-C, and that guest interpreter runs a second
program. The nested execution is meaningful because dispatch and state transitions happen in
ordinary language code. Clearly naming the boundary prevents a demonstration from becoming an
inflated portability claim.
