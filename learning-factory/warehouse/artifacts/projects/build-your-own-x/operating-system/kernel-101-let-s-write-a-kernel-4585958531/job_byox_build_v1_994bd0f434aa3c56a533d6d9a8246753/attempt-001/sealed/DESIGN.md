# Reference design answers

## Frames

The byte array is the ownership record and `free_count` is a cached aggregate. Allocation changes
one zero byte to one and decrements the count; free performs the inverse. Frame zero is valid, so
`-1` is the only failure result. Double free is rejected because accepting it would make the count
disagree with ownership and could permit two future owners.

## Scheduler

`cursor` means “most recently selected slot,” while `current_slot` means “running now.” They are
separate because blocking clears the latter but must preserve fairness history. Slots in `UNUSED`
or `EXITED` are reusable. A new monotonically increasing PID overwrites a reused slot, so a stale
PID no longer matches anything.

## Virtual memory

The reference validates address, permissions, duplicates, and mapping-table capacity before asking
the frame allocator for ownership. Publishing the mapping is then a no-fail sequence of fixed-field
writes. Translation divides into virtual page and offset, checks permission-set inclusion, and
recombines the physical frame with the unchanged offset.

Unmapping first returns the frame. If that fails—indicating inconsistent state—the mapping stays
present so two representations do not both claim success.

## RAM filesystem

Name validation scans at most `TK_NAME_CAPACITY` bytes and requires a terminator within that bound.
Reads preflight file existence, capacity, and output pointer before copying, so an undersized read
does not expose a prefix. Unlink clears name and data even though only metadata removal is externally
required; this avoids stale contents in a reused slot.

## Integration

The same source has two consumers. Native C tests establish state transitions and failure behavior;
the freestanding link establishes absence of an implicit hosted runtime and supplies a real x86
entry point. Only an emulator or hardware boot could establish correct interaction with a bootloader
and VGA device, and that was unavailable during generation.
