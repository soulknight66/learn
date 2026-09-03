# Review findings

Severity is high for callers that control offsets or lengths. Unsigned
addition wraps modulo `SIZE_MAX + 1`, so a huge count can make the sum appear
small and permit out-of-bounds copying. The bug is target-width independent;
choose `offset` near `SIZE_MAX` and a count that wraps the sum below 256.

First reject `offset > capacity`, then reject
`count > capacity - offset`. This contains no overflowing addition. Under the
published contract, `offset == capacity && count == 0` is a successful no-op;
the same offset with any nonzero count returns `OS_ERR_NO_SPACE`.
