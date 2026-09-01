# Concepts

## Separate representations

A compiler becomes easier to reason about when each stage has a narrow contract. Tokens preserve source locations, an AST makes precedence explicit, bytecode removes syntax, and the VM handles runtime types. Test the boundary between stages rather than relying only on end-to-end output.

## Recursive-descent parsing

Each precedence level is one parser method. A method parses its tighter-binding child and then folds repeated operators leftward. Unary operators recurse at their own level, which makes `!!true` and `---1` possible without special cases. The parser should fail at the earliest token that cannot continue a valid production.

## Binding and lexical scope

Parsing establishes grammatical structure; compilation resolves names. A stack of scope maps lets inner declarations shadow outer ones while assignments select the nearest visible binding. Assigning stable local slots converts name lookup into indexed VM operations.

## Control-flow lowering

Structured `if` and `while` syntax becomes conditional and unconditional jumps. A compiler commonly emits a placeholder target, compiles the body, and patches the earlier instruction when the final address is known. Write down whether the condition is consumed; stack-effect mistakes often hide in loop back-edges.

## VM invariants

A tiny VM is still an untrusted-input boundary. Validate opcode arity, jump targets, stack depth, local indexes, runtime types, arithmetic range, and an execution budget. Ruby-specific shortcuts can violate the language: in Ruby, `%` with a negative dividend and `/` on integers do not directly express Pebble's truncation rule.

## Language design as observable behavior

Rules about shadowing, truthiness, overflow, and error timing are part of the language. If they are implicit, different implementations will silently define different languages. Treat each rule as a testable decision.
