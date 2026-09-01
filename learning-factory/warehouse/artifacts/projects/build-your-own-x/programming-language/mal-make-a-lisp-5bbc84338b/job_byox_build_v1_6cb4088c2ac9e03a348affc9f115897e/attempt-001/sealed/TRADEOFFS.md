# Reference tradeoffs

## Chosen: wrapper symbols

A `Symbol(name)` wrapper costs an allocation per occurrence but prevents host string equality from
changing language semantics. Interning was rejected because it adds global state without helping this
small implementation.

## Chosen: value trees without source spans

Tokens retain positions, while parsed lists do not. Reader failures are precise, but later evaluation
errors cannot cite source locations. A production frontend would use syntax nodes carrying spans and a
separate lowering step to values. The compact tree keeps the parsing milestone approachable.

## Chosen: recursive evaluator with explicit budgets

The implementation closely mirrors language structure and makes scope rules legible. It does not
perform tail-call elimination, and sufficiently high custom limits can encounter Python’s recursion
boundary; that exception is translated to `EVAL_CALL_DEPTH`. A trampoline or explicit continuation
stack would give a fully host-independent call ceiling at considerably greater complexity.

## Chosen: absolute jumps

Absolute instruction indexes make disassembly and validation simple. Inserting instructions after
patching would invalidate them, so compilation only appends and patches after branch layout is known.
Relative offsets would ease bytecode relocation but make review less direct.

## Chosen: compiler subset fails closed

Unsupported stateful and binding forms raise `COMPILE_UNSUPPORTED`. An implicit interpreter fallback
would accept more programs, but “VM mode” would cease to prove that execution went through compiled
code.

## Chosen: simple error codes

One class with stable codes is easy for tests and callers. A hierarchy could improve typed recovery;
structured source spans, causes, and notes would be natural extensions. Error prose is intentionally
informative but non-normative.
