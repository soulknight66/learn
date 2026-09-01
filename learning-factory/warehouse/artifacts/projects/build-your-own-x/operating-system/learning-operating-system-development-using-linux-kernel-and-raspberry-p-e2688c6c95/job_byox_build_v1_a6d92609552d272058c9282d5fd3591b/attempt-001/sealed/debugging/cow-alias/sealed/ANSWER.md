# Copy-on-write alias: sealed answer

The write path is treating `COW` as ordinary write permission without first privatizing the writer's frame. It must validate the entire range, count every touched COW mapping whose frame has more than one reference, verify that enough free frames exist, and only then split mappings.

For the one-page case, copy the complete old frame into the lowest free frame, set the child's entry to that frame, decrement frame 0 from two references to one, and replace `COW` with `WRITE` only in the child's entry. The parent keeps frame 0 and remains COW until it writes; because it then has the sole reference, that later write can replace `COW` with `WRITE` in place. For a two-page store requiring two splits, one available frame means the call fails without changing either entry, either count, or any byte.
