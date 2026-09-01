# Code-review exercise

Review this intentionally flawed open/truncate sequence against `REQUIREMENTS.md`:

```c
file = lookup(name);
if ((flags & PEBBLE_OPEN_TRUNCATE) != 0u) {
    file->size = 0u;
    memset(file->data, 0, sizeof(file->data));
}
fd = first_free_fd(process);
if (fd < 0) {
    return PEBBLE_ERR_NO_SPACE;
}
install_fd(process, fd, file, flags);
```

List the externally observable failure, identify all validation/resource checks that must precede truncation, and propose a regression test that proves byte-for-byte failure atomicity. Also review how the code should behave when the name is missing and `CREATE` is present but the file table is full.

The review answer and corrected ordering are retained in this exercise's sealed material.
