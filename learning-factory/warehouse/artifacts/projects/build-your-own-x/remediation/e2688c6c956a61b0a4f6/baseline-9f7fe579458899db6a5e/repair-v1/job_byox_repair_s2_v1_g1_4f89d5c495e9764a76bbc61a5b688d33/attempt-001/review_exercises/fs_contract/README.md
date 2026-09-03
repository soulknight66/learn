# Review: concise filesystem range check

Review this candidate precondition for an API using unsigned `size_t`:

```c
if (offset + count > MINIOS_FS_FILE_CAPACITY) {
    return OS_ERR_NO_SPACE;
}
```

Report correctness, security, and testability findings. State a concrete input
class that matters on both 32-bit and 64-bit targets, propose a safer check,
and note whether a zero-length write at capacity should pass.
