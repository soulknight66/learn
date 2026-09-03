# Write atomicity review

Copy-until-full implements a partial write while returning an error, contradicting the contract and
making rollback difficult. Check that the descriptor cursor is valid, then use subtraction to test
`count > capacity - offset` without overflowing. Only after that check should bytes, cursor, size, and
the output count change. Exact-boundary writes succeed; the next byte fails without mutation.
