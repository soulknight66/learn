# Ember-C conformance requirements

## 1. Scope

Implement an interpreter in C17 for the language below.  The implementation
must compile source to the specified bytecode and execute it in a bounded stack
machine.  It must not invoke a system C compiler on guest input.

An Ember-C translation unit is ASCII source of at most 1,048,576 bytes.  It has
one function, `int main()`, no parameters, and no top-level declarations.

## 2. Lexical grammar

Whitespace, `//` line comments, and `/* ... */` block comments are ignored.
Block comments do not nest.  An unterminated block comment is an error at its
opening delimiter.  Identifiers match `[A-Za-z_][A-Za-z0-9_]*`; the first 63
bytes are significant and longer identifiers are rejected.  Decimal integer
literals range from 0 through 9223372036854775807 with no suffixes.

Keywords are `int`, `main`, `if`, `else`, `while`, `return`, `print`, `arg`,
`load`, and `store`.  Operators and punctuation are:

```text
( ) { } ; , = + - * / % ! == != < <= > >= && ||
```

## 3. Syntax

```text
program      := "int" "main" "(" ")" block EOF
block        := "{" statement* "}"
statement    := block
              | "int" IDENT ("=" expression)? ";"
              | IDENT "=" expression ";"
              | "if" "(" expression ")" statement ("else" statement)?
              | "while" "(" expression ")" statement
              | "return" expression ";"
              | "print" "(" expression ")" ";"
              | "store" "(" expression "," expression ")" ";"
expression   := logical-or
logical-or   := logical-and ("||" logical-and)*
logical-and  := equality ("&&" equality)*
equality     := comparison (("==" | "!=") comparison)*
comparison   := term (("<" | "<=" | ">" | ">=") term)*
term         := factor (("+" | "-") factor)*
factor       := unary (("*" | "/" | "%") unary)*
unary        := ("!" | "-" | "+") unary | primary
primary      := INTEGER | IDENT | "(" expression ")"
              | "arg" "(" expression ")"
              | "load" "(" expression ")"
```

Declarations have lexical block scope.  A name may shadow one in an outer
block but may not be redeclared in the same block.  A name is not in scope in
its own initializer.  All paths may fall through `main`; that is equivalent to
`return 0;`.  The nearest unmatched `if` owns an `else`.

Syntax nesting is bounded independently of source size.  The outer `main`
block is level 1.  Each nested block, `if` or `while` statement, unary operator,
parenthesized primary, and `arg(...)` or `load(...)` primary adds one active
level.  Level 256 is accepted; attempting to enter level 257 is a compile-time
error located at that construct's opening token.  The fixed delimiters of
`main`, conditions, `print`, and `store` do not add a level by themselves.

## 4. Values and effects

Values are signed 64-bit integers.  Relational, equality, and logical results
are exactly 0 or 1.  Zero is false; every nonzero value is true.  `&&` and `||`
evaluate left-to-right and short-circuit.  Other binary operands evaluate
left-to-right.

Locals initialize to zero when no initializer is present.  `arg(i)` returns
the ith guest argument, or zero when `i` is nonnegative and outside the supplied
argument list.  A negative argument index is a runtime error.  `print(v)` emits
the canonical decimal representation followed by one newline.  `load(i)` and
`store(i,v)` access a zero-initialized 4096-cell heap; invalid indices are
runtime errors.  `store` has no expression form.

Addition, subtraction, multiplication, unary negation, division, and remainder
must detect signed overflow.  Division or remainder by zero is an error, as is
`INT64_MIN / -1` or `INT64_MIN % -1`.  There are no implicit wraparound
semantics.

## 5. Deterministic limits

- syntax nesting depth of at most 256 levels, as defined above;
- at most 256 simultaneously allocated local slots;
- at most 65,536 bytecode words;
- operand stack capacity of 4,096 values;
- heap capacity of 4,096 values;
- default execution budget of 1,000,000 bytecode instructions.

Exceeding a limit is a compile-time or runtime error, never memory corruption.
Every bytecode jump target must be within the code array.  Stack underflow and
overflow must be diagnosed.

## 6. Bytecode ABI

Each instruction and operand occupies one signed 64-bit word.  Jump targets are
absolute word offsets.  The required opcodes are:

| Value | Name | Following word / stack effect |
|---:|---|---|
| 0 | `HALT` | stop successfully |
| 1 | `PUSH` | immediate; push it |
| 2 | `LOAD_LOCAL` | slot; push local |
| 3 | `STORE_LOCAL` | slot; pop into local |
| 4..8 | `ADD SUB MUL DIV MOD` | pop rhs, lhs; push result |
| 9..14 | `EQ NE LT LE GT GE` | pop rhs, lhs; push 0 or 1 |
| 15..16 | `NEG NOT` | replace top value |
| 17 | `JMP` | absolute target |
| 18 | `JZ` | target; pop and jump when zero |
| 19 | `PRINT` | pop and print |
| 20 | `ARG` | pop index; push argument or zero |
| 21 | `HLOAD` | pop address; push heap cell |
| 22 | `HSTORE` | pop value, then address; store |
| 23 | `POP` | discard top |
| 24 | `RETURN` | pop result and stop successfully |

`HALT` is accepted by the VM but need not be emitted by the compiler.  A
compiler-generated fallthrough pushes zero and emits `RETURN`.

## 7. Interface and diagnostics

The executable must support:

```text
emberc SOURCE [-- INTEGER ...]       compile and run
emberc --check SOURCE                compile only
emberc --tokens SOURCE               print one token per line
emberc --emit SOURCE OUTPUT          write bytecode as decimal words
emberc --tower SOURCE                run SOURCE with its own bytecode as input
emberc --max-steps N SOURCE [-- ...] change the execution budget
```

`N` is a decimal integer from 0 through `UINT64_MAX`.  A zero budget is valid:
the source is compiled, then execution fails before dispatching its first
opcode.  Each dispatched opcode costs one step; operand words cost none.
Negative, malformed, and out-of-range budgets are usage errors.

`--tokens` lines are `line:column KIND lexeme`; EOF has an empty lexeme.  User
errors return a nonzero process status and a single primary diagnostic on
standard error beginning `path:line:column:`.  Runtime faults begin exactly
`path:line:column: runtime error:` using the source path and the location of the
faulting opcode; budget exhaustion before the first dispatch uses that first
opcode's location.  Usage errors may omit a source location.  No diagnostic
text beyond these stable prefixes is prescribed.

For `--tower`, argument zero is 0 and arguments 1 onward are the compiled words
of `SOURCE`.  A guest bytecode interpreter can therefore read word `pc` with
`arg(pc + 1)`.  The supplied milestone program arranges for a nested `arg(0)`
to evaluate to 1, selecting its finite base case.
