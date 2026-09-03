# Code-review exercises

## Transactional output parameters

Review a proposed `cairn_translate` change that assigns `*physical_out = 0` at entry, then searches for
a mapping. List all contract violations visible when translation fails and propose tests using a
sentinel output and a byte snapshot of kernel state.

## Atomic fixed-capacity writes

Review a proposed file write loop that copies until it reaches `CAIRN_FILE_CAP`, advances the cursor
for each byte, and finally returns `CAIRN_ERR_NO_SPACE`. Decide whether its behavior matches the
all-or-nothing contract. Consider an overwriting write, an exact-boundary write, and an overflowing
addition.

Solution-bearing reviews are under the matching directories in `sealed/review_exercises/`.
