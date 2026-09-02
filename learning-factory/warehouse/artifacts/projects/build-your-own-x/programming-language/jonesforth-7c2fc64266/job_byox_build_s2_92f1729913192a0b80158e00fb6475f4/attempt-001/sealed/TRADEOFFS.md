# Reference tradeoffs

## Fixed tables versus allocation

Fixed storage makes every upper bound explicit, removes allocator and libc dependencies, and enables
simple boundary tests. It also wastes some name space and prevents dictionary growth. For this
educational contract, auditable failure is more valuable than dynamic capacity.

## Linear lookup versus hashing

Linear lookup is O(words × name length), but 23 primitives and 64 user words keep the bound small.
A hash table would improve scaling while adding collision policy, tombstone state, and more memory
invariants unrelated to the core interpreter/compiler lesson.

## Cell bytecode versus native compilation

Cell bytecode makes literal operands and branch patching visible and portable across executions of
the fixed binary. Native x86 emission would teach instruction encoding and executable-memory policy,
but would obscure the language-design milestones and introduce W^X and relocation concerns.

## Absolute targets versus arena offsets

The reference stores absolute branch targets because it links as a non-PIE ET_EXEC and never
serializes compiled words. Arena-relative indexes would be easier to validate, relocate, and persist;
they are the preferred direction for a hardened or PIE implementation.

## Read-all input versus streaming

Reading the bounded stream before evaluation makes token slices stable and exact input enforcement
straightforward. It delays execution until EOF and is unsuitable for an interactive REPL. A
production design would use a refillable input abstraction with explicit token-copy lifetime.
