# Reference design

MicaOS Core Lab separates three bounded state machines behind one C11 header. The design is deliberately small enough to inspect completely: every resource lives in a caller-owned fixed array, every successful transition is deterministic, and every fallible operation reports one of the eight declared status values.

## Shared rules

The reference follows these rules in all modules:

1. Initialization overwrites every observable field, so prior storage bytes do not matter.
2. Required pointer validation occurs before dereference. A rejected operation leaves state and outputs unchanged.
3. Range checks use subtraction after an upper-bound check rather than unchecked addition. For example, a file write is valid only if `offset <= 128` and `length <= 128 - offset`.
4. Allocation scans from the lowest array index. This makes resource selection reproducible.
5. Released RAMFS bytes and VM frames are cleared. A later owner cannot observe old contents.
6. The core includes only its own header and calls no libc routine.

Error categories are used consistently: malformed arguments are `MICA_ERR_ARG`, exhausted fixed storage is `MICA_ERR_FULL`, an unknown identity or absent mapping/file is `MICA_ERR_NOT_FOUND`, an illegal transition or inconsistent internal record is `MICA_ERR_STATE`, duplicate creation/mapping is `MICA_ERR_EXISTS`, numeric bounds failures are `MICA_ERR_RANGE`, and a write through read-only protection is `MICA_ERR_PERM`.

## Scheduler

The scheduler owns eight stable records. `cursor` records the slot chosen by the last successful schedule. Initialization sets it to slot 7, so scanning strictly after it chooses slot 0 first. A successful schedule examines each slot at most once, wrapping modulo eight. READY and the single RUNNING record are eligible; the selected record becomes RUNNING and any prior RUNNING record becomes READY.

The lifecycle is:

```text
UNUSED --spawn--> READY --schedule--> RUNNING
                     |                   |
                     +------block--------+--> BLOCKED --wake--> READY
                     |                   |         |
                     +-------exit--------+---------+--> EXITED --reap--> UNUSED
```

More precisely, both READY and RUNNING may block, and READY, RUNNING, or BLOCKED may exit. An EXITED record remains occupied and retains its code until reap. Wake accepts only BLOCKED; reap accepts only EXITED. Schedule itself performs `RUNNING -> READY -> RUNNING` when a time slice is reconsidered.

PIDs are nonzero 32-bit values selected from `next_pid`. Spawn skips identities that are currently live, including after numeric wrap, and changes `next_pid` only after a record is successfully created. Slot reuse therefore does not immediately revive a stale PID. A validation pass rejects impossible enum values, zero live PIDs, duplicate live PIDs, an invalid cursor, or multiple RUNNING records before any scheduler mutation.

`inspect` and `get` are aliases by behavior: both copy one complete process record and never change scheduling order.

## Virtual memory model

The VM object is the physical allocator: eight `64`-byte arrays plus an eight-entry used map. Each address space is a 16-entry page table. A mapped entry stores a frame index and one writable bit.

Map validates the virtual page and duplicate state, scans for the lowest unused frame, clears it, marks it used, and publishes the page entry last. If no frame exists, neither object changes. Unmap validates the entry and allocator accounting, clears the frame, returns it to the free set, and resets the entry.

A linear virtual address is split as:

```text
virtual_page = address / 64
page_offset  = address % 64
```

Addresses 0 through 1023 are valid. Resolution rejects an unmapped page or a page entry whose frame is outside the allocator or marked free. Read publishes its output only after resolution succeeds. Write resolves first, then tests the page's writable bit before touching the byte.

Normal API use gives every mapping a distinct frame, so pages and address spaces are isolated. Because the teaching API exposes concrete structs and has no ownership table, bytewise-copying a live address space is outside the supported lifecycle; see the production review.

## Flat RAM filesystem

The RAMFS is an array of eight file records. Each record contains a used bit, a 16-byte name buffer (15 bytes plus terminator), 128 data bytes, and a logical size. Creation and lookup compare bytes exactly. The validator scans no more than 16 bytes, rejects empty or overlength input, `/`, `.`, and `..`, and requires a terminator within the limit.

Create rejects a duplicate before selecting the lowest free record. Unlink clears the entire record. Stat copies only the logical size and leaves its output untouched on error.

Write is offset-based and never truncates a suffix. A positive write beyond the old EOF fills the gap with zero and sets size to `max(old_size, offset + length)`. Length zero succeeds without a data pointer or size change when the offset is at most 128. Bounds are checked before lookup or mutation. Up to 128 input bytes are staged in a local array before any file byte changes; this also gives deterministic behavior when input aliases the destination record.

Read accepts an offset through EOF. It copies `min(destination_capacity, size - offset)` bytes and reports that exact count. A zero-capacity read permits a null data destination but still requires `out_read`. Offset beyond EOF and every other rejected read leave both destination and count unchanged.

## Complexity and storage

All loops have fixed small bounds. Scheduler and file lookup are `O(8)`, page mapping is `O(8 + 64)`, byte access is `O(1)`, and a filesystem read/write is `O(128)` worst case. Storage is entirely embedded in the public module objects; there is no heap, recursion, clock, randomness, host service, or hidden global state.
