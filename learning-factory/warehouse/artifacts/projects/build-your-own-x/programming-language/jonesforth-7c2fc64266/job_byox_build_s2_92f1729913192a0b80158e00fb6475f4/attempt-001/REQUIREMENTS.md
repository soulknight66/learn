# Cinder language contract

## Process interface

- Target x86-64 Linux. The executable has no command-line options and reads source from file
  descriptor 0 until EOF.
- Accept at most 65,536 input bytes. Empty input succeeds with status 0 and no output.
- Language output goes only to descriptor 1. Diagnostics go only to descriptor 2.
- Any lexical, compile-time, runtime, or resource-limit error exits with status 2 and a nonempty
  diagnostic. The implementation need not recover after the first error.

## Tokens and integers

- Bytes from `0x00` through ASCII space (`0x20`) separate tokens.
- A `#` encountered while seeking the next token begins a comment through newline or EOF. Within a
  token, `#` is an ordinary byte.
- Tokens and word lookup are case-sensitive. User-word names contain 1–31 bytes.
- An integer is an optional `-` followed by one or more decimal digits, and must lie in the signed
  64-bit range. A bare `-` is the subtraction word. Out-of-range digit strings are errors, not names.

## Data model

- Cells are signed 64-bit two's-complement values. The data stack holds at most 256 cells.
- `+`, `-`, and `*` wrap modulo 2^64.
- `/` returns a signed quotient truncated toward zero. `mod` returns the corresponding signed
  remainder. Division by zero and `INT64_MIN / -1` are errors.
- Comparisons produce `-1` for true and `0` for false.

The primitive words and stack effects are:

```text
+ - * / mod             ( a b -- result )
= < > 0=                ( a b -- flag ), except 0= is ( a -- flag )
and or xor               ( a b -- result )
invert                   ( a -- result )
dup drop swap over rot   standard Forth stack effects
depth                    ( -- current-depth )
.                        ( n -- ), print signed decimal then newline
.s                       ( -- ), print bottom-to-top cells separated by spaces then newline
emit                     ( n -- ), write the low byte
cr                       ( -- ), write a newline
```

## Definitions and control flow

- `: name ... ;` compiles a new word. Definitions are visible only after their terminating `;`.
- A compiled integer pushes a literal; a primitive compiles its operation; an existing user word
  compiles a call. `recurse` compiles a call to the definition currently being built.
- `if ... then` consumes a flag and executes its body only when nonzero.
- `if ... else ... then` selects exactly one body. These forms may nest.
- `;`, `if`, `else`, `then`, and `recurse` are compile-only. `:` is interpret-only. Reserved control
  names, primitive names, and existing user names cannot be redefined.

Implement at least 64 completed user definitions, 8,192 compiled cells, 64 nested control-flow
patches, 256 active user-word calls, and 1,000,000 VM instructions per top-level user call. Exceeding
a bound must diagnose an error before an out-of-bounds write or nontermination.

## Determinism examples

```text
1 2 + .                         => 3\n
: sq dup * ; -9 sq .            => 81\n
: sign dup 0 < if drop -1 else 0 > if 1 else 0 then then ;
-8 sign . 0 sign . 7 sign .     => -1\n0\n1\n
```
