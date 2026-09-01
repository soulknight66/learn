# Expected review

**Block / memory-safety:** `bytes + alignment - 1` can wrap before masking. For `SIZE_MAX`
and alignment 16 the helper returns zero, so a nonzero request can be treated as a zero/tiny
allocation and later overwritten by the caller. Reject zero/non-power-of-two alignments and
check `bytes > SIZE_MAX - (alignment - 1)` before addition. Add boundary tests around every
supported alignment. The separate demonstration records the overflow without writing through
the resulting size.
