# Concepts behind MiniOS

## Processes are state machines

A process table is not just an array of callbacks. Each slot has identity and
a legal state. Scheduling, blocking, wakeup, exit, and reap form controlled
transitions; accepting an impossible transition often creates two running
processes or loses a task forever. MiniOS makes this state machine explicit and
uses monotonically increasing PIDs so a newly spawned process is not silently
confused with a reaped one.

Round-robin scheduling illustrates preemption and fairness without requiring a
timer interrupt. `current_slot` is a cursor as well as an ownership claim. A
correct scheduler updates the old owner, searches from the following slot, and
publishes exactly one new owner.

## Virtual memory is checked indirection

Real page tables are hardware-defined trees. The lab uses a small linear table
but preserves their essential semantics: addresses divide into a page number
and offset, mappings must be aligned, translation preserves the offset, and
permissions are checked before producing a physical address. Virtual and
physical range checks are deliberately different.

The permission argument is a mask, not an enum. A mapping with read and write
access satisfies a read request and a combined read/write request, but not an
execute request. Validate unknown bits before consulting mappings so malformed
requests have deterministic errors.

## Filesystems turn names into persistent objects

The RAM filesystem has no disk, directories, or crash recovery, yet it still
demonstrates namespace uniqueness, bounded metadata, byte-range I/O, sparse
gap semantics, and unlinking. Its fixed file slots resemble an inode table;
names identify occupied slots and data persists across API calls.

Atomic rejection matters even in a toy filesystem. If an oversized write
copies a prefix before reporting failure, callers cannot retry safely. Check
the whole request first, then mutate. Production filesystems extend this idea
with locking, journaling or copy-on-write, and durable write ordering.

## Model versus hardware

These subsystems are deterministic models. A hardware-capable kernel would
also need exception vectors, privilege transitions, context save/restore,
cache and TLB maintenance, frame allocation, device drivers, synchronization,
and a persistent block format. The sealed integration build only demonstrates
that the model can execute freestanding on an emulated AArch64 machine; it is
not a claim of Raspberry Pi compatibility.
