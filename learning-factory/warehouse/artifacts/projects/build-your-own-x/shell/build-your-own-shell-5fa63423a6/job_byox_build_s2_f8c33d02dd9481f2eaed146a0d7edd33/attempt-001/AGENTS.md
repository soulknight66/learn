# Learner and agent guide

Work only in the implementation directory you control. Treat the public tests as examples of the contract, not as its full definition.

## Build discipline

- Compile with C17, POSIX interfaces enabled, and warnings treated as errors.
- Keep ownership explicit: every successful lexer/parser allocation must have exactly one documented release path.
- Use `fork`, `execvp`, `pipe`, `dup2`, `setpgid`, `tcsetpgrp`, and `waitpid` directly. Do not invoke another shell or use `system`/`popen`.
- Pass subprocess arguments as arrays. Never assemble a shell command string.
- Close every unused pipe end in both parent and child.
- Write deterministic tests for malformed syntax as well as happy paths.
- Do not weaken, delete, or special-case tests.

## Completion discipline

Record the exact build and test commands you ran. A zero exit from a worker is not evidence of correctness; only the external harness may assign validation labels. Keep generated build outputs out of submitted source artifacts.
