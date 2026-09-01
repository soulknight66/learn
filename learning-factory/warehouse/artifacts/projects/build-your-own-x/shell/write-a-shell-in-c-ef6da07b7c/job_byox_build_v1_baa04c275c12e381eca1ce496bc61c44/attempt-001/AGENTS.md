# Solver guidance

Work in `starter/` unless a test command explicitly reads another learner-visible directory. Do not inspect or copy anything under a directory named `sealed`; that content is reserved for independent evaluation.

Preserve these constraints:

- Build with the warnings in `starter/Makefile`; do not silence warnings to make the build pass.
- Keep parsing independent from process creation so malformed input never partially launches a pipeline.
- Every allocation, file descriptor, child PID, and terminal handoff needs a clear owner and cleanup path.
- Use `fork`, `execvp`, `pipe`, `dup2`, `setpgid`, `waitpid`, and `tcsetpgrp` directly. Do not invoke a host shell through `system`, `popen`, or `sh -c` to implement the requested behavior.
- Diagnostics belong on standard error. Prompts are interactive-only.
- Do not weaken or edit public tests to claim completion. Add your own tests beside your implementation if useful.

Recommended loop:

```sh
make -C starter clean all
python3 public_tests/test_shell.py --shell starter/msh --stage parsing
```

Then advance through the remaining test classes documented in `public_tests/README.md`.
