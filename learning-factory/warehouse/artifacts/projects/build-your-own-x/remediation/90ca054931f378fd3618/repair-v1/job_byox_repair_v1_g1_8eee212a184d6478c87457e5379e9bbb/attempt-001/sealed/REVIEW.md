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
- The lexical-token capacity excludes EOF and has a separately allocated sentinel slot.
- Source-controlled expression and statement recursion is checked before descent; unary prefix
  parsing is iterative.
- Test processes run in new sessions with whole-group cleanup and bounded output files.

## Repair generation 1

The first independent review returned `REVISE`: a 32,760-pair expression could exhaust the 8 MiB
host stack, EOF consumed one advertised token slot, runner timeouts did not contain descendants,
the starter accepted signed/space-prefixed budgets that the reference rejected, and two prose
boundaries were unclear. This generation adds normative nesting limits and boundary regressions,
reserves EOF separately, shares a process-control helper across both runners, gives starter and
reference the same digit-only CLI parser, corrects the milestone link, and states the generated-file
educational permission precisely. These are builder-local repairs pending a fresh independent
review; they do not overturn or relabel the archived verdict.

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
- POSIX rlimits apply per process, and process groups do not contain a hostile descendant that
  deliberately creates a new session. The supplied runner is stronger test containment, not a
  production sandbox or cgroup boundary.

## Disposition

Repaired generated reference material, awaiting fresh independent validation. Not productionized.
Do not interpret the passing local suite as security assurance or as an independent completion
label.
