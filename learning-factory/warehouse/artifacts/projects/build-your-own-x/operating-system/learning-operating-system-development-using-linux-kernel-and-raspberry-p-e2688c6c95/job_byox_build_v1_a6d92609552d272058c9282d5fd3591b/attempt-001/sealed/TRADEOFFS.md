# Sealed tradeoffs and alternatives considered

## Fixed capacity versus allocation

Fixed arrays waste space and impose small limits, but remove allocator failure from most transitions and make exhaustive capacity tests practical. A real kernel would use slab/page allocators and would need rollback across more failure points.

## Exposed structures versus opaque handles

The public structure lets learners inspect state and lets corruption tests exercise the invariant checker. The cost is weak encapsulation: arbitrary writes can create states that mutating APIs are not all hardened to consume. Production code should hide layouts behind an internal boundary and validate data crossing trust domains.

## Linear lookup versus indexing

PID, file, and free-slot lookup are linear. With limits of 8 or 32, this is predictable and clearer than maintaining additional indices whose consistency must also be checked. Larger systems should use generation-tagged handles and suitable lookup structures.

## Independent fork cursors versus POSIX sharing

Fork copies each descriptor and its cursor. POSIX instead shares an open-file description, including the offset. Independent cursors make ownership and open-count accounting easier for this lab, but code must not assume the behavior matches Linux.

## Busy unlink versus deferred reclamation

Rejecting unlink while open avoids detached-but-live file records. Unix filesystems permit unlink and reclaim the inode after the last reference. Supporting that behavior would require namespace-link counts separate from open references.

## Error codes versus assertions

Public APIs return deterministic errors for caller-controlled invalid input and exhaustion. Internal impossible states produce `PEBBLE_ERR_CORRUPT` in selected paths, while the checker provides comprehensive diagnosis. Assertions were avoided because they would terminate a test process and erase evidence about later cases.

## Host model versus hardware-first development

Pure C mechanisms are fast to test and sanitize. They cannot validate exception entry, register context, TLB maintenance, device ordering, linker placement, or firmware interactions. The Pi boot probe remains a separate, explicitly partial adapter.
