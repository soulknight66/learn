# Diagnosis

Snapshot the complete file after first writing a known 256-byte pattern. Issue
the 10-byte write at offset 250 and require `OS_ERR_NO_SPACE`, zero bytes
reported, unchanged size, and byte-for-byte equality with the snapshot. Then
retry a valid six-byte write and require exactly those six bytes to change.

The fix is preflight, not rollback: reject when `offset > capacity` or
`count > capacity - offset` before zero-filling or copying anything. The
subtraction form cannot be bypassed by unsigned addition overflow.
