# Concepts to master

## Tokens before trees

A lexer turns bytes into tokens while preserving source positions.  Keeping
location handling in one layer prevents every parser branch from inventing its
own line accounting.  Maximal munch matters for pairs such as `!=` and `!`.

## Precedence without an AST

Recursive-descent functions can emit postfix bytecode directly.  Each
precedence level compiles its tighter subexpression first, then emits the
operator.  This saves an AST but makes error recovery and later optimization
harder.

## Forward jumps are promises

An `if` cannot know its end offset when `JZ` is emitted.  Reserve an operand,
compile the body, then patch the reserved word.  A `while` combines one backward
jump with a patched forward exit.

## Scope and storage are different

Removing a name from the compile-time symbol table at `}` does not require
erasing its runtime slot.  A new declaration can reuse or consume another slot
as long as all bytecode references remain stable.

## The VM is an untrusted-input boundary

Even compiler-produced bytecode should be checked by the VM.  Bounds checks,
valid opcodes, checked arithmetic, and a step budget turn malformed programs
from memory-safety bugs into deterministic diagnostics.

## What the tower demonstrates

The final guest program implements the documented VM dispatch loop using only
Ember-C constructs.  The native implementation compiles it and supplies those
same bytecode words as data.  The guest loop then executes its own bytecode and
reaches a finite base branch.  This is a semantic fixed point at the bytecode
boundary—not a claim that Ember-C parses all ISO C or reads its own source.
