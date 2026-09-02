# Prefix Forge requirements

This file is the normative learner contract. Examples illustrate behavior but do
not exhaust the accepted or rejected inputs.

## 1. Source language

Input is UTF-8 text, at most `MaxSourceBytes` bytes. A program contains one or
more expressions. Its grammar is:

```text
program  = expression { expression } EOF
expression = integer | string | boolean | call
call     = "(" identifier { expression } ")"
integer  = ["-"] digit { digit }
boolean  = "true" | "false"
string   = '"' { string-character | escape } '"'
escape   = "\\" ( '"' | "\\" | "n" | "r" | "t" )
identifier = lower { lower | digit | "_" | "-" }
```

Whitespace is space, tab, carriage return, or newline. A semicolon outside a
string begins a comment through the next newline. Integer values must fit in
`int64`. Strings may contain UTF-8; positions are measured in bytes. Any other
character, invalid UTF-8, invalid escape, or unterminated string is an error.

Lines and columns are one-based; offsets are zero-based. Columns count bytes,
including bytes inside a multi-byte rune. A span is half-open: `Start.Offset` is
included and `End.Offset` is excluded. The EOF token has a zero-width span.

Parsing is limited to `MaxNesting` simultaneously open calls. Empty input,
unexpected `)`, a missing closing `)`, an empty call, and a non-identifier in
operator position are errors.

## 2. Built-ins and static types

There are three value types: `number`, `string`, and `boolean`. Calls must use
exactly these built-ins:

| Built-in | Arguments | Result | Evaluation |
| --- | --- | --- | --- |
| `add`, `sub`, `mul`, `div` | number, number | number | eager, checked arithmetic |
| `lt` | number, number | boolean | eager |
| `eq` | T, T | boolean | eager; both argument types must match |
| `and`, `or` | boolean, boolean | boolean | short-circuit |
| `not` | boolean | boolean | eager |
| `concat` | string, string | string | eager |
| `if` | boolean, T, T | T | evaluate only the selected branch |
| `print` | T | T | write the displayed value and newline once |

Unknown names, wrong arity, wrong argument types, and unequal `if` branch types
are check errors. `div` truncates toward zero. Division by zero and every `int64`
overflow (including `MinInt64 / -1`) are runtime errors. Boolean display is
`true` or `false`; number display is base ten; a string displays its contents
without quotes. `print` propagates writer errors. A nil output writer suppresses
output.

A multi-expression program evaluates left to right and returns only its last
value. Earlier values are discarded, but their effects still occur.

## 3. Required Go API

The module path and package name supplied in `starter/` must remain
`example.com/prefixforge` and `prefixforge`. Preserve all exported declarations
and field names in the scaffold, including:

```go
func Tokenize(source string) ([]Token, error)
func Parse(tokens []Token) (Program, error)
func Check(program Program) ([]ValueType, error)
func Compile(program Program) (Bytecode, error)
func Run(code Bytecode, out io.Writer) (Value, error)
func Evaluate(program Program, out io.Writer) (Value, error)
func Execute(source string, out io.Writer) (Value, error)
```

`Tokenize` includes one final `TokenEOF`. `Parse` requires that EOF token and
rejects tokens after it. `Compile` performs checking itself and emits a final
`OpHalt`. Compiled `if`, `and`, and `or` must preserve lazy/short-circuit
behavior. `Bytecode.String` must produce stable, one-instruction-per-line output
with four-digit zero-based instruction indexes.

`Run` treats bytecode as untrusted. Before or during execution it must reject an
unknown opcode, invalid jump target, stack underflow, operand-kind mismatch,
invalid halt stack shape, instruction count over `MaxInstructions`, stack growth
over `MaxStackDepth`, or execution over `MaxSteps`. It must return errors rather
than panic. Jump targets are absolute indexes into `Bytecode.Code`.

All user-facing pipeline failures use `*StageError`, preserve the most relevant
source span, and set `Stage` to one of `lex`, `parse`, `check`, `compile`, `vm`,
or `eval`. Exact prose is not prescribed, but it must identify the cause.
`errors.As` must work through any contextual wrapping.

## 4. Command-line program

`cmd/prefixc` accepts `-mode tokens|ast|bytecode|run|eval`. It reads one optional
source argument, otherwise standard input. Unknown modes, extra arguments,
pipeline failures, and input larger than the source limit exit nonzero and write
a diagnostic to standard error. `run` and `eval` preserve program `print` output
and then write `=> VALUE` on its own line. The inspection modes must be stable
across repeated runs.

## 5. Quality constraints

- Use only the Go standard library; tests must not need a network connection.
- Never use `panic` for malformed source or bytecode.
- Do not use global mutable compiler or VM state.
- Do not silently recover from malformed input or emit partial bytecode as a
  successful result.
- Keep interpreter and VM observable behavior identical for every valid program.
- Add deterministic tests for boundary positions, nesting, lazy effects,
  arithmetic failure, malformed bytecode, and writer failure.

The local starter/public checks are only partial evidence. Independent hidden
validation remains required.
