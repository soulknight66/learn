# Code-review exercise: cross-page copy

Review this intentionally flawed pattern:

```c
while (remaining != 0) {
    pte = lookup(address);
    if (!pte || !(pte->flags & WRITE)) return MK_ERR_PERMISSION;
    memcpy(frame_bytes(pte, address), source, chunk_for_page(address, remaining));
    /* advance address, source, and remaining */
}
```

List correctness and security findings, rank their severity, and describe tests that distinguish a
fixed implementation. Focus on failure atomicity, numeric range validation, permission/error
semantics, and overlapping pointers. A sealed review contains the reference findings.
