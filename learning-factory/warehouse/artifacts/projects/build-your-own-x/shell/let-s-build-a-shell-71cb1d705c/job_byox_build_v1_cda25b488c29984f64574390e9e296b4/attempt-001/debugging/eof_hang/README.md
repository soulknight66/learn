# Debugging lab: output without exit

`buggy.c` creates a producer, a consumer, and one pipe. The consumer prints the
complete message, but the program does not return to the prompt.

From this exercise directory, build and reproduce:

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -O0 -g buggy.c -o buggy
timeout 2 ./buggy
printf 'status=%s\n' "$?"
```

If `timeout` is unavailable, run `./buggy` and interrupt it after the message is
visible. A system-call tracer is optional; filtering for `close`, `read`,
`write`, and `wait4`/`waitpid` is especially useful.

Answer these before editing:

1. Which process is blocked, and in which operation?
2. What condition would let that operation complete?
3. For each process, which pipe descriptors should remain open after `fork`?
4. Why is receiving all currently buffered bytes different from receiving
   end-of-file?

Success means the exact payload is printed once, the program exits zero without
a timeout, and repeated runs leave no children behind.
