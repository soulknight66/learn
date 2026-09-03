# Debugging case: failed write changes data

A proposed `fs_write` loop copies while space remains, then returns
`OS_ERR_NO_SPACE` if bytes are left. A 10-byte request at offset 250 therefore
copies six bytes before failing.

Design a regression test that distinguishes this behavior from the contract.
Your test must inspect both file length and existing bytes after the error, and
it should include a retry that would be safe only if the first call were
atomic.
