# Ripple requirements

## 1. Public API

`starter/compiler.js` is a CommonJS module exporting:

- `CompilerError`
- `tokenize(source)`
- `parse(sourceOrTokens)`
- `analyze(ast)`
- `optimize(ast)`
- `generate(ast, analysis?)`
- `compile(source, options?)`
- `interpret(sourceOrAst)`
- `pipeline(source, options?)`

`compile` returns a JavaScript **function body**. Invoking that body returns an array containing values from Ripple's `emit` statements. `options.optimize === false` disables optimization; optimization is enabled otherwise. `pipeline` returns `{ tokens, ast, optimizedAst, analysis, code }`.

`analyze` returns `{ ast, symbols, declarationIds, referenceIds }`. `symbols` is an ordered array of `{ id, sourceName, generatedName }`; the two ID tables are `WeakMap`s keyed by declaration statements and identifier-use nodes. This keeps the AST serializable, so a rewritten AST must be analyzed again before generation.

## 2. Lexical grammar

Input is a JavaScript string. Tokens have `{ kind, value, line, column, offset }`; line and column are one-based and offset is a zero-based UTF-16 index. An `EOF` token with value `null` is always last.

Token kinds are `KEYWORD`, `IDENTIFIER`, `NUMBER`, `STRING`, `OPERATOR`, `PUNCTUATION`, and `EOF`.

- Keywords: `let`, `emit`, `true`, `false`.
- Identifiers: ASCII letter or `_`, followed by ASCII letters, digits, or `_`.
- Numbers: one or more digits, optionally followed by `.` and one or more digits. Exponents and leading-dot forms are outside the language.
- Strings: double quoted. Supported escapes are `\\`, `\"`, `\n`, `\r`, and `\t`. Raw newlines and unknown escapes are errors.
- Operators: `+ - * / % ! == != < <= > >= && || =`.
- Punctuation: `( ) , ;`.
- Spaces, tabs, CR, and LF are ignored. `//` begins a comment through the next LF or end of input.

The scanner must always consume input or throw; malformed text may never make it loop forever.

## 3. Syntax

```text
Program        -> Statement* EOF
Statement      -> "let" IDENTIFIER "=" Expression ";"
                | "emit" Expression ";"
Expression     -> Or
Or             -> And ("||" And)*
And            -> Equality ("&&" Equality)*
Equality       -> Comparison (("==" | "!=") Comparison)*
Comparison     -> Term (("<" | "<=" | ">" | ">=") Term)*
Term           -> Factor (("+" | "-") Factor)*
Factor         -> Unary (("*" | "/" | "%") Unary)*
Unary          -> ("!" | "-") Unary | Call
Call           -> Primary ("(" Arguments? ")")*
Arguments      -> Expression ("," Expression)*
Primary        -> NUMBER | STRING | "true" | "false"
                | IDENTIFIER | "(" Expression ")"
```

The AST uses `Program`, `LetStatement`, `EmitStatement`, `BinaryExpression`, `UnaryExpression`, `CallExpression`, `Identifier`, and `Literal` nodes. Every node has a `loc` copied from its first token as `{ line, column, offset }`. A `Program` has `body`; declarations have `name` and `initializer`; emits have `expression`; operators have `operator`, `left`/`right` or `argument`; calls have `callee` and `arguments`; identifiers have `name`; literals have `value`.

## 4. Static semantics

Bindings become visible only after their initializer. Reject duplicate declarations, reads of unknown names, and declarations whose names collide with built-ins. A call target must be a bare built-in name; variables are not callable.

Built-ins and arities:

| Name | Arity | Meaning |
| --- | --- | --- |
| `abs` | exactly 1 | absolute value |
| `sqrt` | exactly 1 | square root |
| `pow` | exactly 2 | exponentiation |
| `min` | at least 1 | numeric minimum |
| `max` | at least 1 | numeric maximum |
| `len` | exactly 1 | Unicode code-point length of a string |

`len` throws a runtime `TypeError` for non-strings. Other numeric built-ins and arithmetic follow JavaScript number behavior. `+` follows JavaScript primitive addition. Equality is strict (`==` means JavaScript `===`; `!=` means `!==`). `&&` and `||` short-circuit and return an operand value.

## 5. Optimization and generation

The optimizer returns a new AST and may constant-fold unary and binary expressions only when doing so preserves Ripple behavior. It must not mutate its input. Non-finite numeric results must remain as expressions so the generator never needs a non-finite literal.

Generation must:

- start with `"use strict";`;
- use internal variable names derived from semantic binding IDs, not source names;
- map built-ins from a fixed table rather than emitting a source-provided callee;
- JSON-escape string literals;
- return emitted values in order from an internal output array;
- preserve short-circuit and precedence behavior.

## 6. Interpreter and errors

The interpreter evaluates the checked AST directly and returns emitted values. It must not call `eval`, `Function`, `vm`, or the generated program.

User-source failures throw `CompilerError` with stable fields `phase`, `code`, `line`, `column`, and `offset`. Phases are `lex`, `parse`, or `analyze`. Codes should be specific and stable; the required cases exercised publicly include `LEX_UNEXPECTED_CHARACTER`, `PARSE_EXPECTED_EXPRESSION`, `ANALYZE_UNKNOWN_IDENTIFIER`, and `ANALYZE_DUPLICATE_BINDING`.
