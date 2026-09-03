# Reference review

Review performed against the independently generated requirements and sealed tests, not against the linked resource.

## Confirmed properties

- Parser and lexer destructors are null-safe and idempotent after zeroing.
- Parser strings remain valid after the token list is released.
- Child execution uses `execvp` with an argument vector and never routes text through another command interpreter.
- Pipeline descriptors are closed in parent and child; low-descriptor pressure is exercised by the sealed CLI suite.
- Explicit redirection occurs after pipe hookup and therefore wins deterministically.
- Parent and child both attempt process-group placement.
- The foreground terminal is handed off and restored on the tested Ctrl-C path.
- `cd` and `exit` execute in the parent only under the documented constraints.
- Partial launch cleanup targets the process group and waits for recorded children.

## Open risks

- There is no persistent job table or user-facing recovery for stopped jobs.
- Background completion notices and job identifiers are minimal.
- Interactive behavior was exercised on one local PTY scenario, not across diverse kernels or terminal configurations.
- Allocation-failure branches were inspected but not deterministically fault-injected.
- No sanitizer, race detector, coverage threshold, fuzzing campaign, or performance benchmark is promoted as validation evidence.
- Diagnostics are stable enough for humans but are not a versioned machine-readable interface.

These open risks prevent a production-readiness claim. The manifest intentionally remains `GENERATED` + `PARTIAL`; external validators control any stronger label.
