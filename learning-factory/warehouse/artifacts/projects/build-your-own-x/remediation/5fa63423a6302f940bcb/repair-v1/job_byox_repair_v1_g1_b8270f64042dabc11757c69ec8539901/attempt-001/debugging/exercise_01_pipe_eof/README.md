# Exercise 1: the reader that never reaches EOF

`buggy.c` launches the equivalent of a two-stage producer/consumer pipeline.
The consumer prints `payload`, but the parent can wait forever afterward.

Tasks:

1. Draw a table of both pipe endpoints after each `fork`, marking which process
   owns each descriptor.
2. Explain why the consumer's `read` cannot return zero after the producer
   exits.
3. Identify the smallest parent-side correction.
4. Generalize the correction for an N-stage pipeline, including descriptors
   duplicated with `dup2`.
5. Propose a regression test that detects the hang without allowing the test
   suite itself to hang indefinitely.

Compile with:

```sh
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror \
  -o pipe-eof buggy.c
```

Treat the executable as expected to hang until you have patched it.

