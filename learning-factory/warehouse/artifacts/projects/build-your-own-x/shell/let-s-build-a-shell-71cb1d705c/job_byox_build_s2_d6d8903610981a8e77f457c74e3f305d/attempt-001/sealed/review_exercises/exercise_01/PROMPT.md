# Exercise 01: review foreground waiting

Review this proposed wait loop in a shell that also has background jobs:

```c
while (live_foreground_children > 0) {
    pid_t pid = waitpid(-1, &status, WUNTRACED);
    if (pid > 0) {
        update_foreground_job(pid, status);
        --live_foreground_children;
    }
}
```

List correctness failures, state assumptions that the replacement should make
explicit, and describe a safer selection strategy.
