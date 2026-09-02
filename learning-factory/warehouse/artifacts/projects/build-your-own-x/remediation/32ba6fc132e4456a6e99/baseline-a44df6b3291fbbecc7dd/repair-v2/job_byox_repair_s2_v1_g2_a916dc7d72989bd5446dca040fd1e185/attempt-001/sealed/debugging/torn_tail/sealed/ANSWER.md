# Sealed answer: the disappearing corruption

The loop violates evidence preservation and can roll back an acknowledged
history: a complete frame with a checksum mismatch is corruption, not proof of
an interrupted append. Segment position alone cannot distinguish those cases.

The decoder should return explicit `CLEAN_EOF` and `TORN_TAIL` outcomes only
when required bytes are absent, while complete invalid bytes raise a corruption
exception. Recovery may truncate only `TORN_TAIL`, and only in the final
segment. It must propagate corruption and any incomplete non-final segment.

A regression test writes and forces one valid frame, flips a payload byte
without changing file length, asserts reopen throws `CorruptLogException`, and
asserts file size and damaged bytes remain unchanged. A separate test truncates
the last few bytes and verifies final-tail repair retains the valid prefix.
