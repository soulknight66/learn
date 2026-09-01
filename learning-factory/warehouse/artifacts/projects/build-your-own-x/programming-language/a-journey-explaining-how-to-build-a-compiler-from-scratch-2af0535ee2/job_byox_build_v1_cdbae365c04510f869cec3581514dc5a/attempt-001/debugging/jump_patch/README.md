# Exercise: the drifting jump target

The pseudocode in buggy_patch.txt records code_count after emitting a placeholder and later patches
that recorded value. Determine which instruction is overwritten and how this can turn a false branch
into fall-through. State the stack depths required at the true path, false label, and merge.
