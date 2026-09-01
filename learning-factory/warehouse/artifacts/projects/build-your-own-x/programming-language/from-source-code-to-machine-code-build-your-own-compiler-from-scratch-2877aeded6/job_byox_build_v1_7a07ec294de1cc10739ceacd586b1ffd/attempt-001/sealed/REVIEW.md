# Sealed implementation review

Review scope: the generated reference implementation and its test/CLI boundary. This is internal review
material, not an independent validation label.

## Findings addressed

- Binary validation completes before VM state or output is touched.
- Jump operands are checked against decoded instruction starts, not merely numeric range.
- Both branch edges participate in stack-depth merge analysis, and unreachable bytes are rejected.
- Signed division avoids floating point and distinguishes truncation from Python floor division.
- The `bool` subtype is explicitly rejected for instruction limits and slot-count arguments.
- Source compilation errors occur before destination temporary-file creation; replacement is same-directory
  and cleanup runs on write or replace failure.
- CLI subprocess tests use argv arrays, captured output, and ten-second timeouts.
- No dynamic evaluation, shell command strings, network calls, secret inputs, or host-dependent locale
  parsing occur in the compiler or VM.

## Known limitations

- Deeply nested unary expressions, blocks, or parentheses can reach Python's recursion limit.
- Source length, AST size, compile time, decoded instruction count, and output volume are not bounded.
- Validation constructs an instruction object and dictionary entry per opcode; hostile multi-gigabyte
  files must be limited before this library boundary.
- The step limit does not sandbox output callbacks or provide process isolation.
- Diagnostics provide one point rather than recovery, spans, or multiple errors.
- The binary has no checksum, feature flags, debug table, authenticity mechanism, or forward-compatible
  section directory.
- Atomic replacement preserves content integrity but does not promise metadata preservation or directory
  fsync durability after sudden power loss.

These limitations are why `productionized` remains false and validation labels remain `GENERATED` and
`PARTIAL`.
