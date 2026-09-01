# Starter implementation

This directory supplies stable interfaces, ownership helpers, a strict build, and an intentionally incomplete parser/executor. It compiles before you begin so that each failure after that is attributable to behavior, not missing scaffolding.

Build and inspect the baseline:

```sh
make -C starter clean all
printf 'printf hello\\n' | starter/msh
```

The baseline accepts the command-line shape and handles empty input, but reports nonempty commands as unimplemented. Complete the `TODO(stage ...)` sites in this order:

1. `src/parser.c`: tokenize and validate the complete input line.
2. `src/shell.c`: execute external commands and concurrent pipelines.
3. `src/shell.c`: run parent built-ins and normalize status.
4. `src/jobs.c`: retain, update, print, wait for, and free jobs.
5. `src/shell.c`: establish process groups and interactive terminal ownership.

Do not change the public types merely to avoid an ownership problem. You may extend them, split source files, or add private helpers. Keep `msh_parse_line` free of process-related side effects.

The starter does not represent a partial reference solution and is expected to fail most public tests.
