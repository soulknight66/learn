# Diagnosis: rejected write changed a file

Bounds validation occurred after the copy or after updating the recorded size. A rejected operation
must decide whether the complete interval fits before mutating either data or metadata. Check the
offset, length, and overflow-safe remaining capacity first; only then copy bytes and extend the size.

The regression creates a file with sentinel content, snapshots its size and bytes, attempts an
offset-based write that crosses `MICA_FILE_CAPACITY`, and compares the complete observable state with
the snapshot.

The invariant is failure atomicity: a non-`MICA_OK` write has no filesystem-visible effect.
