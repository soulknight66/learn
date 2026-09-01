# Sealed design answers

1. The process-state map is authoritative; the queue and `current` are indexes
   that `validate` cross-checks in stable PID/queue order. A queue entry must
   exist and be `Ready`, every `Ready` PID must occur once, and the sole
   `Running` PID must equal `current`.
2. R2.3 defines `schedule` as a scheduling point: the current process is
   appended before the oldest ready process is selected. Thus one process
   remains itself, while two or more rotate fairly.
3. The root remains the only table, both tentative parent entries remain zero,
   and the one temporarily allocated frame is returned. Allocator free and
   allocated counts equal their pre-call values.
4. Index extraction discards the upper address bits. Without an earlier
   canonicality check, invalid and valid addresses could select the same three
   indices and become aliases.
5. Page-table pages are metadata owned by `Sv39`; the data frame is owned by
   its caller. `unmap` dismantles metadata and returns the data-frame identity
   so that its owner can decide whether to free, remap, or retain it.
6. In this model an intermediate PTE has exactly `VALID` and names a known
   table frame. A leaf has `VALID`, at least one of R/W/X, obeys W-implies-R,
   and names a physical data page.
7. Empty/relative syntax, bad separators, dot components, NUL, and component
   length are lexical errors. They can all be rejected before inode traversal.
8. Checked addition applies uniformly. `usize::MAX + 0` does not overflow, but
   its end offset exceeds any smaller configured limit and yields
   `FileTooLarge`; `usize::MAX + 1` yields `RangeOverflow`. This avoids a special
   empty-write path.
9. Resolve and type-check the parent; prove the child entry and inode exist;
   reject a nonempty directory; only then remove the parent link and inode.
   There is no fallible work after publication begins.
10. Hard links replace unique reachability with reference counts. Duplicate
    traversal becomes valid for files, directory links need stricter cycle
    rules, removal decrements link count, and reclamation occurs only at zero
    links (and, in a real kernel, zero open references).
11. Process state plus run queue need one scheduler lock or equivalent atomic
    protocol. Filesystem directories/inodes need namespace and object locks.
    A simple order is scheduler lock never held across filesystem work, then
    ancestor directories root-to-leaf, then inode/data locks by inode number.
12. State machines, checked arithmetic, canonical address validation,
    ownership boundaries, and failure atomicity transfer. Host collections do
    not model page-table memory ordering, `sfence.vma`, interrupt races, TLBs,
    DMA, partial device failures, persistent ordering, or crash recovery.
