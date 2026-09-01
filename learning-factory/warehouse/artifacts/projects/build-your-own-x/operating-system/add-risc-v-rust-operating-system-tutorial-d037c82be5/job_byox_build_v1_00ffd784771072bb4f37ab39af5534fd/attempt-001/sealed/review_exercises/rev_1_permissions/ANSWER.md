# REV-1 answer

`intersects(R | W)` means either bit is sufficient, so a read-only page passes a
write request. It also ignores which access was requested, permits no execute
check, and omits `USER` for user-mode translation. Mapping validation separately
rejects W without R, but translation still must require the exact access bit.

For each request, the required leaf bit is R, W, or X respectively; a missing
bit denies. Independently, `user == true` requires U, while supervisor access in
this simplified contract does not. `VALID` and legal leaf encoding are checked
before this matrix.
