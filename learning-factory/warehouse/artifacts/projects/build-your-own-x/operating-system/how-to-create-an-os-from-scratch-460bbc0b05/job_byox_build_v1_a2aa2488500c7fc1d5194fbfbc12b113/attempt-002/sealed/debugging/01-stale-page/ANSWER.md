# Diagnosis: stale bytes after mapping

The allocator reused a physical frame without clearing all `MICA_PAGE_SIZE` bytes. Page-table state can
be correct while data confidentiality is still broken: unmapping changes reachability, not the bytes in
the frame.

A minimal regression maps a writable page, fills its final byte, unmaps it, maps another virtual page,
and reads both byte zero and the final byte. Both must be zero. The clearing loop belongs after a free
frame has been selected and before its page-table entry becomes present, so no reachable mapping can
observe partly cleared storage.

The invariant is: every successful map initially exposes a page containing only zero bytes.
