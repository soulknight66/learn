# Exercise 01: the reader never exits

The following reduced pipeline setup prints its data, but the `cat` process
waits forever. Assume all omitted error checks succeed. Identify which process
owns the descriptor keeping the stream alive and propose the smallest safe
fix.

```c
int channel[2];
pipe(channel);
if (fork() == 0) {
    dup2(channel[1], STDOUT_FILENO);
    close(channel[0]);
    execlp("printf", "printf", "payload", NULL);
}
if (fork() == 0) {
    dup2(channel[0], STDIN_FILENO);
    close(channel[1]);
    execlp("cat", "cat", NULL);
}
close(channel[0]);
wait(NULL);
wait(NULL);
```
