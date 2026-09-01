# Sprig language contract

Implement the supplied `sprig` Python package. All behavior below is observable unless explicitly
called implementation-defined.

## 1. Reader

`tokenize(source)` returns `Token` objects with `kind`, `text`, one-based `line`, and one-based
`column`. Recognized tokens are `LPAREN`, `RPAREN`, `QUOTE`, `ATOM`, and `STRING`.

- Space, tab, carriage return, newline, and comma separate tokens.
- `;` begins a comment through the next newline, except inside a string.
- `'form` is reader shorthand for `(quote form)`.
- Strings are delimited by `"` and support exactly `\\`, `\"`, `\n`, `\r`, and `\t` escapes.
- An unsupported escape is `READ_BAD_ESCAPE`; an unfinished string is `READ_UNTERMINATED_STRING`.
- Signed base-ten integers matching `[+-]?[0-9]+` become Python integers. `true`, `false`, and `nil`
  become their corresponding Sprig literals. Every other atom becomes a `Symbol`.
- `read_one` accepts exactly one form. No form is `READ_EMPTY`; trailing forms are `READ_TRAILING`.
- `read_all` accepts zero or more forms. A stray `)` is `READ_UNEXPECTED_CLOSE`; a missing `)` is
  `READ_UNCLOSED_LIST`. A parser nesting limit must fail with `READ_DEPTH` before host recursion leaks.

Reader errors expose a stable `code`; where a source token exists they also expose `line` and
`column`.

## 2. Values and printing

Sprig values are integers, booleans, strings, `nil`, symbols, lists, builtins, and functions. Symbols
and strings are distinct even when their spelling matches. `print_value` emits readable values:

| Value | Output example |
| --- | --- |
| false / true / nil | `false`, `true`, `nil` |
| integer | `-12` |
| string | JSON-style quoted text, including escapes |
| symbol | its unquoted name |
| list | `(item1 item2)` |
| builtin / function | stable opaque form such as `<builtin:+>` / `<function>` |

Printing a value and reading it again must preserve all data values (callables excluded).

## 3. Evaluation

`Evaluator(max_steps=10000, max_call_depth=200)` owns deterministic budgets. Each call to `evaluate`
starts a fresh step and call-depth budget. Exhaustion raises `EVAL_STEP_LIMIT` or
`EVAL_CALL_DEPTH`; Python recursion errors must not escape.

Evaluation uses a lexical `Environment`. Unbound reads raise `NAME_UNBOUND`; redefining with `def`
is allowed. An empty list evaluates to itself. A non-list literal evaluates to itself, while a symbol
is looked up.

Special forms have these exact shapes:

```lisp
(quote form)
(if condition then-form [else-form])
(do form ...)
(let ((name init) ...) body-form ...)
(fn (parameter ...) body-form ...)
(def name value-form)
(set! name value-form)
(and form ...)
(or form ...)
```

- Only `false` and `nil` are falsey.
- Omitted `if` else, empty `do`, empty `and`, function bodies with no forms (which are rejected), and
  empty `or` produce respectively `nil`, `nil`, `true`, an `EVAL_FORM` error, and `nil`.
- `if`, `and`, and `or` short-circuit and return values rather than coerced booleans.
- `let` initializers are evaluated left-to-right in the new child environment, so later bindings can
  see earlier ones. Binding names and function parameters must be unique symbols.
- Functions close over the environment where `fn` runs. Calls use a fresh child environment and exact
  arity. `set!` updates the nearest existing binding and never creates one.
- For a regular call, evaluate the callee before arguments, and arguments from left to right.
- Wrong special-form shape raises `EVAL_FORM`; calling a non-callable raises `EVAL_NOT_CALLABLE`;
  function arity errors use `EVAL_ARITY`.

## 4. Builtins

`default_environment()` contains these names:

- Integer arithmetic: `+`, `-`, `*`, `/`. `+` and `*` accept zero or more operands; unary `-`
  negates; `/` needs at least two operands and truncates toward zero after each division. Division by
  zero is `BUILTIN_DIV_ZERO`. Booleans are not integers.
- Ordered integer comparisons: `<`, `<=`, `>`, `>=`, each with at least two operands and chain
  semantics.
- `=` takes exactly two values and compares structural data values. Symbols and strings are distinct;
  callables compare only by identity.
- Lists: `(list ...)`, `(head list)`, `(tail list)`, `(cons value list)`, `(empty? list)`, and
  `(count list)`. `head` and `tail` on an empty list return `nil` and `()` respectively.
- Logic/type: `(not value)` uses Sprig truthiness; `(type value)` returns one of the symbols `nil`,
  `boolean`, `integer`, `string`, `symbol`, `list`, `builtin`, or `function`.

Builtin arity failures use `BUILTIN_ARITY`; type failures use `BUILTIN_TYPE`. Builtins must not leak
host exceptions.

## 5. Compiler and VM

`Compiler.compile(form)` supports literals, symbol loads, `quote`, `if`, `do`, and ordinary calls.
It rejects `def`, `set!`, `let`, `fn`, `and`, and `or` with `COMPILE_UNSUPPORTED`. An empty list may be
compiled as a literal. The result is a `Bytecode` object ending in `RETURN`; jump targets are absolute
instruction indexes and `disassemble()` is deterministic.

`VirtualMachine(max_steps=10000).run(bytecode, env=None)` implements that bytecode. Loads use the
provided environment or a new default environment. A VM program must leave exactly one result;
malformed bytecode raises a `VM_*` language error rather than a host exception. Only builtins are
callable from compiled code; any other callee raises `VM_NOT_CALLABLE`. VM step exhaustion is
`VM_STEP_LIMIT`.

For every expression in the supported subset, evaluator and VM must yield structurally equal results
or the same documented language-error category.

## 6. Command line

`python3 -m sprig [-e SOURCE] [--engine eval|vm] [--disassemble] [FILE]` is the interface.

- `-e` and `FILE` are mutually exclusive. With either, parse all forms in order using one environment,
  print each result on its own line, and exit 0.
- With neither, start a prompt-based REPL. EOF exits 0. Blank/comment-only submissions print nothing.
- `--engine vm` applies to every form and therefore rejects forms outside the compiler subset.
- `--disassemble` is valid only with `--engine vm`; write a disassembly before each result.
- Reader, evaluation, compile, VM, file, and argument errors go to stderr without traceback and exit 2.
- UTF-8 is used for files. Exact prompt appearance is not part of the contract.

## 7. Constraints

Use no third-party dependency and no host `eval`/`exec`. Keep modules separable so tests can exercise
each phase. Results must be deterministic; do not read environment variables, time, randomness, the
network, or files except the file explicitly supplied to the CLI.
