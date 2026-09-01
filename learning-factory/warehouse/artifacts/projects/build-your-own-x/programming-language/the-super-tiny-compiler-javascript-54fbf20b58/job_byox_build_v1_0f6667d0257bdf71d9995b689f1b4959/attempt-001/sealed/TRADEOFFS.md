# Sealed trade-off analysis

## Parser organization

Layered recursive descent duplicates a small amount of control flow but keeps Pebble's precedence
visible in the source. Pratt parsing would reduce the number of methods and ease adding postfix
operators, at the cost of making binding-power mistakes less obvious to a first-time compiler
author. The reference uses recursive descent because the operator set is closed and small.

## Two execution engines

The evaluator is shorter and is the preferred semantic oracle. The bytecode VM has more moving
parts—stack discipline, jump patching, validation, and instruction budgeting—but separates frontend
and execution concerns and resembles a real compiler target. Keeping both costs maintenance, yet
enables unusually effective differential testing.

## Constants pool versus inline operands

A constants pool makes instructions uniform and keeps literal payloads separate from control data.
It also introduces index validation and can make a tiny artifact larger. Inline literals are simpler
for this number-and-boolean language. The reference uses a pool to make ownership and malformed
operand checks explicit and to leave room for larger immutable constants later.

## Named variables versus numeric slots

Name operands are easy to inspect and preserve runtime semantics for path-dependent declarations.
Resolving variables to numeric slots would produce smaller, faster instructions but needs a separate
binding analysis and decisions about declarations in branches. Named access is appropriate for the
teaching target; slot allocation is a valuable optimization exercise after semantics are stable.

## Bytecode validation

Validating the full program before execution guarantees that a structural error cannot appear after
partial output. It takes an extra linear pass and duplicates a few dispatch assumptions. That cost is
small relative to predictable behavior on hostile bytecode, so the reference validates first.

## Work limits

A deterministic instruction/statement budget is portable and easy to test, unlike a wall-clock
timeout. It is not a fair measure of equivalent effort between the two engines, and different
program transformations can change when it expires. The limit is therefore a safety boundary, not a
language-visible performance guarantee.

## Error stability

Dedicated syntax and runtime classes give callers a stable boundary while allowing clearer message
text to evolve. Numeric error codes would be even more stable but enlarge the API and can distract
from the compiler work. The core contract standardizes classes and important message fragments, not
every character.

