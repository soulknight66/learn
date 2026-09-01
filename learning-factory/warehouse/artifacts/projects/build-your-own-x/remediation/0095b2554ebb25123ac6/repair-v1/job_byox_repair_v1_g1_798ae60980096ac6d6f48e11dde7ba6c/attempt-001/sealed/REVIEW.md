# Sealed implementation review

## Summary

The reference is structured around the written stage boundaries and supplies real implementation, black-box tests, adversarial tests, fuzz targets, and benchmarks. Manual review found no deliberate bypass of parsing, analysis, compilation, or validation. State used by compilation and execution is local to a call.

## Correctness review

- Scanner movement is byte-based and handles CR as ordinary whitespace and LF as the only line reset.
- Parser input validation precedes cursor access and canonicalizes no caller input.
- Line-changing positions are bounded by available bytes, and a regression test covers the independently reported forged column-99 stream.
- Analysis inserts a declaration only after its initializer, while duplicate detection happens at the declaration occurrence.
- Expression lowering is left-to-right and statement effects balance the stack.
- Validator range checks precede every local access and avoid allocation by caller-supplied slot count.
- VM arithmetic covers add, subtract, multiply, divide-by-zero, and the signed division overflow.
- Runtime errors discard buffered output, and successful empty output is non-nil.
- Permanent starter tests no longer demand stub behavior. Separate locked tests target a harness-selected learner module; oracle tests remain explicitly separate.
- A strict learner-view allowlist, deterministic constructor, unit coverage, and bubblewrap isolation probe replace the former prose-only disclosure boundary.

## Risks requiring independent execution

The repair host lacked Go, so the code could not be compiled, formatted by `gofmt`, raced, fuzzed, benchmarked, or executed here. Static/manual inspection is not a substitute for those observations. In particular, another environment must run the harness self-check and candidate tests, verify Go syntax and exact coordinates, and exercise race/fuzz behavior before assigning any stronger label. Bubblewrap availability alone is also not isolation evidence; the recorded probe must pass on the final learner view.

## Non-production findings

- There are no resource limits for source size, nesting depth, AST size, instruction count, locals, or output count.
- Recursive parsing, analysis, and compilation can exhaust the Go stack on hostile nesting.
- Diagnostic messages are stable enough for this contract but are not localized and do not include source excerpts.
- Bytecode is an exported mutable struct, so validation must repeat for every run.
- There is no versioned serialization, compatibility policy, tracing, cancellation, observability, or embedding hardening.
- The CLI buffers the full source and full output.

The appropriate status is therefore generated and partial, not tested, reviewed-by-independent-party, transfer-verified, or productionized.
