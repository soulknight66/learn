# Answer: partial read

The implementation violates the documented atomic failure boundary: callers receive an error but
their buffer has changed, so ignoring failed output is no longer sufficient. Fill a destination
with a sentinel, request one byte less than the file length, assert `-1`, then compare every byte
with the sentinel. Validate capacity and pointer before the copy loop.
