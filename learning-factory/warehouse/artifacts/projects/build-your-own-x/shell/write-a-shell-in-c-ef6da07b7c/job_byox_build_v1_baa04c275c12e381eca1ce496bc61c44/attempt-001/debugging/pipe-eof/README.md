# Exercise: the pipeline that never ends

`broken.c` launches one writer and one reader around a pipe. The reader prints every byte it receives. The program prints the expected payload but does not terminate.

Reproduce safely:

```sh
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror \
  -o /tmp/pipe-eof-exercise debugging/pipe-eof/broken.c
timeout 2 /tmp/pipe-eof-exercise
```

Questions:

1. Which process owns each of the two original descriptors after both forks?
2. What exact condition makes `read` return zero?
3. Why is the writer child's exit insufficient?
4. Identify the earliest correct close point for every unused descriptor.
5. How would the same bug appear in a three-command shell pipeline?

Do not replace the blocking `read` with a timeout or special sentinel; repair ownership so ordinary EOF is correct.
