# Answer: frame leak on duplicate map

Initialize two frames, map page A once, record one free frame, then map A again and assert failure
and an unchanged free count. The violated invariant is failure atomicity: physical ownership moved
even though no mapping was published.

Scan first for both a duplicate and a free mapping slot. Only after every table-level failure is
excluded should the implementation call `tk_frame_alloc`. A rollback strategy can also work, but it
adds a second failure path if frame release itself detects inconsistent state.
