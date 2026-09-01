# Reference design

This is the sealed answer to the design prompts.

## Pipeline and ownership

The CLI reads at most 1,048,577 bytes into one owned source allocation, using the
extra byte only to detect overflow. Tokens contain spans into that allocation.
AST nodes copy tokens, not text, so source, tokens, and the fixed AST arena remain
alive until the selected backend finishes. Cleanup proceeds in the reverse
order.

The phases are strictly ordered:

```text
bounded read -> tokenize -> parse -> validate/assign slots -> run or emit
```

Each phase reports through a fixed-size error buffer and stops at its first
error. Later phases never consume a partially valid result.

## Parser invariants

On success, every expression function leaves the first non-expression token
current. Each statement consumes its complete terminator or blocks. A failed
consume records exactly one diagnostic, after which callers return without
attempting recovery.

One arena of 65,536 `Node` objects holds both expressions and statements. Linked
lists preserve statement order; three generic child pointers represent operands,
conditions, and branches. Explicit parser-depth tracking covers unary recursion,
parentheses, and nested blocks. Validation also rejects a left-deep expression
tree beyond 128 nodes, which bounds recursive backend walks.

## Names and storage

Validation owns a source-order array of at most 256 name tokens. Linear lookup is
bounded and deterministic. It assigns each declaration the next slot and writes
that slot into every use. An initializer is checked before its new name is
inserted, so `let x = x;` fails.

Branches are validated in written order: condition, then block, optional else
block, following statement. Because this intentionally simple language has no
flow-sensitive definite-assignment analysis, every slot begins at zero. Running
a `let` is an assignment to its preallocated slot.

## Defined integer behavior

The interpreter stores values as `uint64_t`. Addition, subtraction,
multiplication, and negation therefore wrap without C undefined behavior.
`memcpy` transfers bit patterns to and from `int64_t` for signed comparisons,
printing, and division. Division handles zero before executing C division and
handles `INT64_MIN / -1` explicitly.

## Interpreter

The tree walker evaluates left before right and executes only the selected
control-flow path. A single counter ticks for every statement visit, including
each reevaluation of a `while` node. The counter makes an empty infinite loop
terminate with the same defined error as a loop with a body.

## Native backend

Variables and the execution counter occupy fixed negative offsets from `%rbp`.
The frame is rounded to 16 bytes. Function entry pushes `%rbp`; subtracting a
multiple of 16 then leaves `%rsp` aligned before every `printf` or `fputs` call.
Expression pushes are balanced before any statement-level call.

Expression generation leaves its value in `%rax`. For a binary node it pushes
the left value, evaluates the right into `%rax`, moves the right to `%rcx`, and
pops the left. Comparisons use signed condition codes. Division guards both zero
and the one overflowing `idivq` pair.

Monotonic numeric labels make emission deterministic. `if` uses false and join
labels. `while` uses a condition/tick label and an exit label. A hidden stack
slot enforces the same statement budget as the interpreter. Error labels print a
fixed message to `stderr`, first reset `%rsp` to `%rbp` to discard any pending
expression temporaries, restore the frame, and return status 1.
