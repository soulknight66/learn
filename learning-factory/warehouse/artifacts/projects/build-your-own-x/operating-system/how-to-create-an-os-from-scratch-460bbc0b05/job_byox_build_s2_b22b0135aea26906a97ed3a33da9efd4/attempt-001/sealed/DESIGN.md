# Reference design decisions

## One object, explicit ownership

All mutable state lives in `struct cairn_kernel`, so independent instances cannot interfere. The
process mapping is the forward view of memory ownership and `frame_owner` is the reverse view. Neither
is treated as a cache: mutations update both, and validation requires a one-to-one match.

## Check, then commit

Each operation separates discovery from mutation. For example, mapping scans for a duplicate virtual
page and remembers a free slot, then checks frame ownership, then checks table capacity. Only after
all three decisions succeed does it write either view. Outputs are assigned last. This ordering makes
the documented error precedence and failure atomicity visible without copying the kernel.

Exit is the one multi-resource transaction. It first verifies every mapped frame so a corrupt frame
cannot cause a partial cleanup. It then releases mappings and descriptors before changing the process
state to `EXITED`.

## Cursor-based scheduling

`current_slot` is both the current-process locator and the round-robin cursor. Blocking and exit keep
the cursor at the previous slot. The scheduler searches before it mutates: it treats the current
running process as eligible when the cyclic scan wraps, selects a candidate, then performs the
demotion/selection pair. Thus a no-runnable result is byte-for-byte transactional.

## Bounded strings and corrupt state

Names are inspected for at most `CAIRN_NAME_CAP` bytes. The validator checks enum, flag, and index
ranges before following a descriptor or frame. This is essential because the public struct layout is
an educational inspection surface and tests may alter it arbitrarily.

## Freestanding boundary

The core defines its own small integer types and uses private byte loops rather than libc. Host tests
compile it as C11; the kernel compiles it for baseline i386 with SSE/MMX disabled. The boot shim alone
contains port I/O and platform-specific assembly.
