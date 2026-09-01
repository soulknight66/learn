# Pebble language and compiler requirements

Normative words **MUST**, **MUST NOT**, and **SHOULD** define the grading contract. The exported declarations in `starter/` are part of that contract.

## 1. Source text and positions

- Input is an arbitrary Go string and may contain invalid UTF-8.
- Only ASCII space, tab, carriage return, and line feed are whitespace.
- A `#` starts a comment that ends immediately before the next line feed or at end of input.
- Identifiers match `[A-Za-z_][A-Za-z0-9_]*` byte-for-byte. `let` and `print` are reserved.
- Integer literals are one or more ASCII decimal digits and MUST fit in signed 64-bit range. Source has no signed literal; write `(- 0 7)` for negative seven.
- Punctuation/operators are `(`, `)`, `+`, `-`, `*`, and `/`. Any other byte starts a `SCAN/INVALID_CHAR` error.
- `Position.Offset` is a zero-based byte offset. `Line` and `Column` are one-based byte coordinates. A line feed advances the line and resets the column to 1; every other byte advances the column by 1.
- `Span.Start` is inclusive and `Span.End` is exclusive. Tokens and AST nodes MUST cover their complete source form. EOF has an empty span at `len(source)`.

Scanning stops at the first error. An out-of-range integer is `SCAN/INTEGER_RANGE` at the literal's start. Error selection MUST be deterministic.

## 2. Grammar

The grammar is:

```text
program     = statement* EOF ;
statement   = "(" "let" IDENT expression ")"
            | "(" "print" expression ")"
            | expression ;
expression  = INTEGER
            | IDENT
            | "(" binary-op expression expression ")" ;
binary-op   = "+" | "-" | "*" | "/" ;
```

There is no implicit grouping, unary operator, assignment, nested `let`, or nested `print`. Top-level expressions are legal and their value is discarded. An empty program is legal.

- The parser MUST consume the entire token sequence and return the first error in source order.
- It MUST reject a missing expression with `PARSE/EXPECTED_EXPRESSION`, an unexpected token with `PARSE/UNEXPECTED_TOKEN`, a missing required token with `PARSE/EXPECTED_TOKEN`, and trailing input after a complete form according to the same grammar.
- It MUST reject a token slice that is empty, lacks EOF, contains a token after EOF, or otherwise cannot have been produced by `Scan`, using `PARSE/INVALID_TOKEN_STREAM`. It MUST NOT panic on a caller-constructed token slice.
- The AST MUST preserve statement order, node kind, identifier/operator data, integer values, and full spans. `Stmt.NameSpan` is populated only for `StmtLet` and covers exactly its declaration identifier; it is the zero-value span for other statements.

## 3. Static analysis

Analysis walks statements and expression children left-to-right.

- A name is visible only after its `let` statement is fully analyzed. Thus `(let x x)` reports `ANALYZE/UNDEFINED_NAME`.
- Declaring an already visible name reports `ANALYZE/REDECLARED_NAME` at the second declaration's identifier.
- Referring to a name not yet visible reports `ANALYZE/UNDEFINED_NAME` at that reference.
- Successful declarations receive slots `0, 1, 2, ...` in source declaration order. `Analysis.Slots` maps each declared spelling to its slot and `SlotCount` equals the number of slots.
- Analysis MUST validate caller-constructed AST values and return `ANALYZE/INVALID_AST`, not panic, for unknown kinds, nil required children, invalid operators, or structurally impossible fields.

## 4. Bytecode compilation

Compilation targets the opcodes declared by the starter. Expressions leave exactly one value on the stack. The observable meanings are:

| Opcode | Operand | Stack effect | Meaning |
| --- | ---: | ---: | --- |
| `OpPush` | integer | +1 | push the operand |
| `OpLoad` | slot | +1 | push an initialized local |
| `OpStore` | slot | -1 | pop into an uninitialized local |
| `OpAdd` / `OpSub` / `OpMul` / `OpDiv` | none | -1 | pop right then left; push result |
| `OpPrint` | none | -1 | pop and append to output |
| `OpPop` | none | -1 | discard a top-level expression result |
| `OpHalt` | none | 0 | terminate |

- Operands are compiled left-to-right. A `let` compiles its initializer then a store; a `print` compiles its expression then a print; an expression statement ends in pop.
- Exactly one halt MUST be emitted, as the final instruction. Empty source compiles to only halt.
- `Instruction.Span` identifies the source construct responsible for the instruction: literals/names use their expression span, arithmetic opcodes use the binary expression span, and statement opcodes use the statement span. Halt uses the program span (empty at 1:1 for an empty program).
- `Compile` MUST reject inconsistent caller-supplied AST or analysis with `COMPILE/INVALID_INPUT`; it MUST NOT silently recompute or repair the analysis.
- Two successful compilations of equivalent inputs MUST produce deeply equal bytecode.

## 5. Bytecode validation

`ValidateBytecode` is a trust boundary and MUST run before execution. It checks the whole linear instruction stream without executing it.

- `SlotCount` MUST be nonnegative. Slot operands MUST be in `[0, SlotCount)`.
- A slot can be stored exactly once and loaded only after it has been stored.
- Non-operand opcodes MUST have operand zero. Unknown opcodes are invalid.
- Every instruction's span MUST contain valid positive line/column values, nonnegative offsets, and an end not before its start.
- Every stack read MUST be provably safe. The stack depth MUST be zero immediately before the final halt.
- There MUST be exactly one halt and it MUST be the final instruction; an empty instruction sequence is invalid.
- Invalid bytecode returns `VALIDATE/INVALID_BYTECODE` at the offending instruction span when one exists. Validation MUST NOT panic or mutate its input.

## 6. Virtual machine

- `Run` MUST validate first, use fresh state on every call, and terminate only at the validated final halt.
- Arithmetic uses signed 64-bit integers. Overflow in add, subtract, multiply, or `MinInt64 / -1` returns `RUN/INTEGER_OVERFLOW` at the arithmetic instruction.
- Division truncates toward zero. Division by zero returns `RUN/DIVISION_BY_ZERO` at the division instruction.
- On any runtime or validation failure, output MUST be `nil`; partially printed values are not observable.
- Successful execution returns a non-nil output slice in print order. A program with no print returns an empty, non-nil slice.
- Repeated and concurrent calls with the same bytecode MUST not interfere with one another. `Run` MUST NOT mutate bytecode.

## 7. Pipeline functions and errors

- `Build(source)` MUST perform scan, parse, analyze, then compile, returning the earliest stage error unchanged.
- `Execute(source)` MUST call the compilation pipeline then the validated VM behavior. It MUST NOT contain a second parser or direct evaluator.
- All language-facing failures MUST be representable as `*pebble.Error`. `errors.As` must work. `Stage`, `Code`, and `Pos` MUST be populated exactly; messages SHOULD be concise and MUST NOT contain nondeterministic map formatting.
- Public functions MUST not panic for arbitrary strings or malformed caller-constructed exported values.

## 8. Command

`cmd/pebble` accepts exactly zero or one path argument. With no path it reads standard input; with one it reads that file. It prints each output integer on its own line to standard output. Usage, I/O, compile, validation, or runtime failures go to standard error and exit nonzero. Successful programs with no output write nothing.

## 9. Constraints

- Use only the Go standard library and Go 1.21-compatible syntax.
- Do not invoke external processes, access the network, or read files from the compiler library.
- Keep all compiler and VM state per call; immutable constants are allowed.
- Complexity SHOULD be linear in source bytes plus AST/instruction count, apart from bounded integer conversion work.
