# Alternative designs

These variants preserve the learning goals but make different contracts or data-structure choices. They are design notes, not additional validated implementations.

## Generation-tagged process handles

Each of eight process slots could carry a generation counter, with the public PID encoding both slot and generation. Lookup becomes constant time and stale slot handles are rejected. The cost is an exposed bit layout, generation-wrap policy, and less obvious monotonically increasing examples.

## Explicit ready queue

A circular queue of slot indexes could make schedule constant time. Block and exit would remove a member; wake would append it. Appending changes the requirement that a woken process resumes at its stable cyclic place, so either the observable policy must change or the queue needs ordered reinsertion.

## VM ownership records

The allocator could store `(address_space_id, virtual_page)` beside every frame. That permits detection of copied or stale PTEs and safe whole-space destruction. It requires stable address-space identities and a `space_destroy(vm, space)` operation absent from the current header. Reference counts would instead permit intentional shared mappings and copy-on-write.

## Sparse or shared zero pages

Read-only mappings could initially point at one global zero frame, allocating a private frame on first write. This greatly increases apparent capacity for zero pages but introduces faults, reference counts, and copy-on-write transitions that obscure this lab's one-mapping/one-frame rule.

## Extent-based RAMFS

Files could own blocks from one shared byte pool rather than embedding 128 bytes per record. Space could be used flexibly, but create/write would gain allocation rollback, fragmentation, and a distinction between per-file and global exhaustion. A persistent variant would additionally need a journal, recovery rules, checksums, and durable ordering.

## Copy-in callbacks

Instead of accepting a raw data pointer, RAMFS could consume data through a callback or a trusted copy-from-user primitive. That creates a place to report partial accessibility without modifying the file. The current all-in-memory lab assumes ordinary accessible C arrays, so a fixed staging buffer is simpler.
