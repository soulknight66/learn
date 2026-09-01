# Adversarial validation notes

Independent validation should emphasize state combinations, not just nominal calls. Useful deterministic families include:

- every legal and illegal process-state edge, with the invariant checker after each call;
- schedule cursors at every slot, sparse ready sets, idle calls, and slot reuse;
- address ranges of length 0, 1, one page, and two pages at each page boundary;
- COW writes with zero, one, and exactly enough free frames, comparing full snapshots on failure;
- every name length around 0 and `PEBBLE_MAX_NAME`, forbidden components, all open-flag subsets, full descriptor and file tables;
- exit/reap after combinations of mappings, forked descriptors, blocked/running state, and open files;
- one-field corruptions of indices, flags, stored counts, and canonical unused records passed only to `pebble_check()`.

The sealed deterministic suite covers representative members. No fuzz campaign was run, no `FUZZED` label is claimed, and a checker pass must not be treated as proof of memory safety under concurrency or hostile hardware.
