# Diagnosis

The parent retains `channel[1]`, the pipe's write end. The consumer reads the
payload and then blocks in its next `read`: the kernel cannot report end-of-file
while any process still has a write descriptor for the pipe. The parent is
simultaneously blocked waiting for the consumer, so neither can make progress.

The relevant invariant is: after forking a pipeline, the supervisor retains no
pipe endpoint that it will not itself use. Each child likewise closes every
unneeded copy after duplicating its endpoints.

Close `channel[1]` in the parent before either `waitpid`. The existing children
already close their unused ends. Merely closing the descriptor after the waits
is too late, and reading the complete payload is not evidence of EOF.

A descriptor trace should show the consumer's final `read` pending and the
parent waiting. After the repair it shows a zero-length `read`, consumer exit,
and successful reap. `fixed.c` contains that focused change.
