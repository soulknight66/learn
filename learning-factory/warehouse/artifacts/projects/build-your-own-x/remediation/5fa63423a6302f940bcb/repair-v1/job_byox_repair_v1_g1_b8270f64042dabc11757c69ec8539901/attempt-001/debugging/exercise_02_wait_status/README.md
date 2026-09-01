# Exercise 2: raw wait status is not an exit code

`buggy.c` runs the command supplied on its command line and returns the integer
written by `waitpid` directly from `main`.

Tasks:

1. Predict what the operating system stores in `status` for a child that calls
   `_exit(7)` and compare it with what the parent process ultimately reports.
2. Explain why checking `status != 0` is insufficient.
3. Define a shell-facing policy for normal exit and signal termination.
4. Patch the wait loop to handle interruption and decode only a status category
   that is actually present.
5. Write tests for exit 0, exit 7, command-not-found behavior, and termination by
   a signal.

Compile and make observations with commands such as:

```sh
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror \
  -o wait-status buggy.c
./wait-status /bin/sh -c 'exit 7'
printf 'reported=%s\n' "$?"
```

