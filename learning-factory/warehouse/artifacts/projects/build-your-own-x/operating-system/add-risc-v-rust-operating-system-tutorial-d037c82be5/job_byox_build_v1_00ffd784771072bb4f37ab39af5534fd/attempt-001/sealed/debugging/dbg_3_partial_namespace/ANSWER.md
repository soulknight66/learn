# DBG-3 answer

Parse the entire path, resolve and type-check the parent, look up the target,
and inspect the target directory before changing either map. If it is nonempty,
return immediately. Once all checks pass, remove the directory entry and inode
with no fallible operation between them. In a storage-backed filesystem this
would require a journal or copy-on-write transaction; the in-memory model relies
on infallible collection removals after validation.

A regression test snapshots recursive listings and inode count, calls
`remove` on a nonempty directory, asserts `DirectoryNotEmpty`, then compares the
full snapshot and calls `validate`.
