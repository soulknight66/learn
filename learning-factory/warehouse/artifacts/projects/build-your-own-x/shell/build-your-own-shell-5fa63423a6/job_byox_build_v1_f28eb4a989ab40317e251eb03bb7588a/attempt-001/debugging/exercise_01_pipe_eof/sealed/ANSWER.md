# Answer: the reader that never reaches EOF

The parent retains `channel[1]`, a write endpoint. Pipe EOF is a property of the
kernel's reference count, not of the intended producer: a read returns zero only
after every descriptor referring to every write endpoint is closed. The
producer exits, but the consumer still sees the parent's possible writer and
blocks in `read`; the parent then blocks waiting for the consumer.

The minimum correction is to close the parent's write copy before either wait:

```c
close(channel[0]);
close(channel[1]);
```

Closing it after `waitpid(consumer, ...)` is too late, because that wait depends
on the close. Closing it only on the normal producer-exit path is also fragile;
the parent has no data role and should release it immediately after the final
fork that needs to inherit it.

For an N-stage pipeline, each child first uses `dup2` to install only its input
and output endpoints, then closes *all* original pipe descriptors. `dup2` adds a
descriptor reference; it does not consume the original. The parent closes each
endpoint as soon as no future child needs to inherit it and closes all remaining
endpoints before waiting.

A regression test should launch the example in a new process group, capture its
stdout, and impose a short deadline. It should require both `payload\n` and
normal termination. On timeout it should kill and reap the entire group so a
failed test leaves no consumer behind. The equivalent shell-level test is a
pipeline whose final stage reads to EOF, repeated enough to expose inconsistent
cleanup.

