# Sealed trade-off analysis

## Exported concrete AST versus interfaces

Concrete tagged structs make black-box tests and deliberate malformed-input tests straightforward. They also force every downstream stage to validate impossible field combinations. Unexported node implementations behind interfaces would encode more invariants but would make this challenge's trust-boundary requirement less visible.

## Prefix syntax versus precedence parsing

Prefix binary forms remove precedence and associativity from parsing, leaving room to focus on token streams, spans, analysis, lowering, and the VM. An infix grammar would be more familiar but would add a precedence-climbing or Pratt parser as a mostly independent concern.

## Bytecode names versus slots

Dense numeric slots make runtime lookup constant and make declaration order visible in compiled output. Retaining names in bytecode would simplify compilation but move name errors or hash-table behavior into execution. Slot allocation becomes more complicated once blocks and reusable lifetimes exist.

## Validation before every run

Revalidating immutable-by-convention bytecode makes `Run` safe for any caller and keeps its public contract simple. It adds linear overhead to repeated execution. A larger system might expose a separate opaque `ValidatedProgram`, but then it must ensure the backing instructions cannot be mutated after validation.

## One-time local stores

Pebble's `let` is immutable, so rejecting a second store turns a source-level property into a bytecode invariant. Supporting assignment would need a separate store opcode or richer validation state; simply loosening the rule would allow bytecode outside the source language.

## Checked arithmetic versus wrapping

Checked arithmetic provides deterministic diagnostics and prevents examples from silently changing meaning near boundaries. Wrapping arithmetic is simpler and sometimes intentional in systems languages, but it would need to be stated as language semantics rather than inherited accidentally from Go.

## Whole-output transaction versus streaming

Buffering output ensures runtime failure exposes no prefix. It costs memory proportional to print count and means the VM API cannot stream unbounded output. A production streaming API would need an explicit partial-effects contract or transactional sink.

## Dependency-free implementation

Standard-library-only code improves offline reproducibility and keeps the educational surface small. Parser generators, assertion libraries, and property-testing libraries could reduce some code but would add supply-chain, versioning, and environment concerns.
