# Sealed alternative designs

Several compatible implementations were considered:

- A bitmap can find free frames compactly, but the required reverse PID lookup would still need a
  separate table.
- Keeping a distinct scheduler cursor and running slot makes their meanings clearer, but enlarges the
  public state and adds another agreement invariant.
- Descriptor generation numbers would allow Unix-like unlink-while-open behavior safely after inode
  reuse. The challenge instead rejects unlink while open.
- Per-inode open counts make unlink checks constant-time but create another value that every open,
  close, and exit path must update transactionally.
- A sorted directory makes lookup faster but turns create/unlink into shifting operations and makes
  byte-for-byte failure atomicity more subtle.

The reference favors the smallest state graph over asymptotic performance because all capacities are
intentionally tiny.
