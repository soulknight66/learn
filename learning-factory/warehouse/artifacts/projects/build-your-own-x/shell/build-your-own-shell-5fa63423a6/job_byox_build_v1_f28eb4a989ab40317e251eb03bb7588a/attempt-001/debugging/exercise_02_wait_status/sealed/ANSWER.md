# Answer: decode wait status by category

The integer filled by `waitpid` is an encoded record. For a normal exit of 7,
`WIFEXITED(status)` is true and `WEXITSTATUS(status)` is 7; the raw value is
commonly 1792. Returning that raw value from `main` lets the operating system
retain only the low exit-status bits, often making the parent appear to have
exited zero. Signal, stop, and continuation information use other encodings.

A conventional small-shell normalization is:

```c
static int command_status(int status)
{
    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return 128 + WTERMSIG(status);
    }
    return 1; /* No final command status was present. */
}
```

The wait itself should retry `EINTR`:

```c
pid_t result;
do {
    result = waitpid(child, &status, 0);
} while (result == -1 && errno == EINTR);
if (result == -1) {
    /* report the wait failure */
}
```

This requires `<errno.h>`. If `WUNTRACED` or `WCONTINUED` is requested for job
control, a returned stop or continuation is a state event, not final pipeline
completion, and must be handled before normalization. A pipeline policy must
also say which stage supplies its logical status; whichever policy is chosen,
all member children still need to be reaped.

Tests should assert the normalized numeric result for normal exits and signals,
not compare raw integers. Command-not-found is emitted by the post-fork exec
failure path and conventionally uses 127; a found-but-unexecutable command can
be distinguished as 126 if the implementation promises that contract.

