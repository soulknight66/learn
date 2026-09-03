# Exercise 01 answer key

`waitpid(-1, ...)` may return a background child. Passing that PID to a
foreground-only updater can corrupt membership state, and decrementing the
counter for stops (or unrelated children) can terminate the loop early. The
loop also ignores `EINTR`, conflates per-process and per-job completion, and
does not define which pipeline member supplies the result.

Assign every foreground pipeline one process group and wait with
`waitpid(-foreground_pgid, ..., WUNTRACED)`. Match the PID to a member record;
mark exits/signals Done and stops Stopped. Continue until every member is Done
or every non-Done member is Stopped. Retry `EINTR`, and derive the shell status
from the last pipeline member's stored raw status. Background changes should
be drained separately at a safe point.
