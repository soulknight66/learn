# Sealed review findings: offset contract

Replica positions and the watermark are end offsets; record offsets name
entries. For five replicas a strict majority is three, so in descending order
the majority position is at zero-based index `2`, which is
`positions.size() / 2`. The proposed `+ 1` selects index `3`, requiring four
copies and under-reporting commitment (and would go out of bounds for some
incorrectly generalized formulas).

A record is committed when `recordOffset < highWatermark`, not `<=`. If the
watermark is 7, offsets 0 through 6 are committed and offset 7 is the first
uncommitted record.

For positions `[9, 9, 7, 4, 0]`, the correct watermark is 7; the proposal picks
4. Assert both that record 6 is committed and record 7 is not. Also test
`[9, 9, 9, 0, 0]` yields 9, watermark monotonicity after stale messages, and
that fewer than three advanced positions cannot move the watermark.
