# Bytecode contract

Instructions are immutable `(opcode, operand)` records. `TICK` records one source-level AST
visit so resource behavior agrees with the tree walker. `CONST`, `LOAD`, arithmetic,
comparison, `NEG`, `NOT`, and `BOOL` push one value. Binary operations pop right then left.
`DEFINE`, `STORE`, and `PRINT` consume one value. Conditional jumps consume their condition.
`JUMP` consumes nothing. `HALT` requires an empty stack.

| Family | Opcodes | Operand |
| --- | --- | --- |
| metering | `TICK` | none |
| values | `CONST`, `LOAD` | integer or name |
| state | `DEFINE`, `STORE`, `PRINT` | name, name, none |
| unary | `NEG`, `NOT`, `BOOL` | none |
| binary | `ADD SUB MUL DIV MOD EQ NE LT LE GT GE` | none |
| control | `JUMP JUMP_IF_FALSE JUMP_IF_TRUE` | absolute instruction index |
| lifecycle | `HALT` | none |

Only `TICK` consumes a public `max_steps` unit. A separate bounded dispatch guard protects the
VM from malformed no-progress cycles. Before execution, verification checks instruction and
operand types, arity, jump targets, reachability, underflow, and stack-height joins. Compilation
of logical operators uses branches; an eager `AND`/`OR` opcode would violate short circuit.
