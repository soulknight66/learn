# Adversarial test missions

After the public suite passes, write black-box tests for these cases without
inspecting sealed material:

1. Generate deterministic process-operation sequences and compare the table to
   a tiny independent state-machine oracle after every call.
2. Exhaust the frame allocator at each intermediate Sv39 allocation point and
   assert exact before/after counts and translations.
3. Map the lowest and highest canonical pages; probe the adjacent noncanonical
   values and every 12-bit offset boundary.
4. Share each possible prefix between mappings, unmap in different orders, and
   verify only empty page-table pages are reclaimed.
5. Generate valid filesystem trees, interleave rejected creates/writes/removes,
   and check that a snapshot of all reachable paths is unchanged after errors.
6. Exercise every malformed path class, checked-addition overflow, zero-length
   I/O, Unicode component, size limit, and nonempty-directory removal.

Use a fixed seed and print the minimal operation trace on failure. Do not use
wall-clock scheduling, random hash order, or network dependencies.
