# Sealed implementation review

## What was reviewed

The reference was checked against the normative grammar and limits, compiled with C11 warnings as
errors, and driven through public and sealed black-box cases. Review focused on host undefined
behavior, stack/frame accounting, patch target validity, error separation, output ordering, and
the nested-interpreter claim.

## Positive findings

- Source size and all fixed table mutations are checked before writes.
- Lexer accumulation rejects an oversized integer before multiplying.
- Signed arithmetic checks occur before host arithmetic that might overflow.
- Function calls preserve lower expression values by recording the argument-base stack index.
- Call resolution completes before the VM can emit output.
- Conditions pop their inputs, and short-circuit merge points publish normalized booleans.
- The guest interpreter uses only ordinary functions, locals, control flow, arithmetic, and print.

## Residual risks

- The implementation has not been fuzzed, model-checked, sanitizer-tested, benchmarked, or tested
  on a second architecture/compiler in this artifact.
- The compiler and VM are large single translation-unit teaching code, which limits modular unit
  testing and makes local reasoning harder.
- Error recovery stops at the first problem; diagnostics are deterministic but not ergonomic for
  editing large files.
- Fixed frames reserve more memory than needed and stack usage is not derived statically.
- Writing output can occur before a later runtime fault; there is no transaction around stdout.
- `fseek`/`ftell` intentionally supports regular seekable inputs only; stdin and pipes are outside
  the CLI contract.

## Disposition

Suitable as generated reference material for independent validation. Not productionized. Do not
interpret the passing local suite as security assurance or as an independent completion label.
