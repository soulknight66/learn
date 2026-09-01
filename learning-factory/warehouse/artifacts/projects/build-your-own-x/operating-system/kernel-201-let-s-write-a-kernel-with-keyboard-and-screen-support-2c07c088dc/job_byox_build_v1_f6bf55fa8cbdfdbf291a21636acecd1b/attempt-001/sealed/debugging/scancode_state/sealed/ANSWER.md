# Answer: sticky extended prefix

The prefix flag is never consumed. `e0 48 1e` emits Up and then attempts to decode `1e` as extended,
so `a` disappears. `e0 20 1e` is worse: the unsupported extended `20` returns before clearing state,
so the later `a` is still treated as extended.

Capture the flag for the current byte and clear persistent state before any mapping/unsupported
return path. Only an unprefixed `e0` should establish state for a future call. A regression should
feed `e0`, assert no event; feed an unsupported extended byte, assert no event; feed `1e`, then assert
a pressed character event with ASCII `a`. A second test should feed `e0 48 1e` and assert Up then `a`.
