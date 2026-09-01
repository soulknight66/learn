# Reference implementation review

Review scope: `sealed/reference/src/mica.c`, its Makefile, and the observable
requirements. This is a generated educational reference, not a production
approval.

## Findings addressed in the artifact

- Signed arithmetic is performed in `uint64_t`, avoiding undefined C overflow.
- Both interpreter and native backend special-case division by zero and
  `INT64_MIN / -1` before a dangerous divide instruction.
- Source, nodes, names, parser recursion, and execution have explicit limits.
- The compiler emits only fixed templates and validated numeric slots; source
  identifiers are never interpolated into assembly.
- Generated calls occur with a 16-byte-aligned stack, and every expression push
  has a matching pop on normal paths. Shared error paths reset `%rsp` from
  `%rbp` before calling the C runtime, safely discarding pending temporaries.
- Compilation is deterministic for identical source bytes.
- Invalid command shapes now return status 2 and emit exactly one
  `mica: usage error:` line; public and sealed tests enforce the CLI contract.
- Accepted whitespace bytes and byte-based position accounting are explicit and
  tested at the vertical-tab/form-feed boundary.
- The complete pack has an exact SHA-256 content inventory with all operational
  files required, and a separate allowlisted learner projection is
  materialized and verified without copying this sealed tree.

## Remaining limitations

- The lexer token vector grows with token count and has no separately stated
  byte budget beyond the source-size limit.
- The AST arena is allocated at its maximum size even for small input.
- Symbol lookup is quadratic in the worst accepted declaration/use pattern,
  though the 256-name cap bounds it.
- Diagnostics use fixed buffers and may truncate an extremely long identifier.
- Assembly was exercised only with the toolchain recorded in `VALIDATION.md`;
  other assemblers and C runtimes were not checked.
- There is no sanitizer, coverage, static-analysis, cross-platform, or
  concurrency evidence in this artifact.
- Output-file creation is not atomic; an I/O failure may leave a partial `.s`
  file.
- Local projection evidence is builder-controlled. Only the external factory
  can establish that an actual learner transfer used the allowlist, so no
  transfer-validation label is claimed.

## Review conclusion

The implementation is suitable as a compact reference oracle for this bounded
challenge. The known limitations and narrow platform target prevent a
production-readiness claim. Independent validation remains required.
