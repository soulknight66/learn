# Sealed trade-off analysis

## In-memory index versus scan-on-read

The reference reconstructs an in-memory list of records and encoded sizes on
open. Reads are simple and deterministic, but memory grows with record count
and external file changes are invisible. A practical log would keep sparse
offset/time indexes, map or pread bounded regions, and validate indexes against
segment identity during recovery.

## Synchronous calls versus asynchronous replication

Acknowledgements are explicit method calls, so tests control ordering and time.
This isolates safety logic from scheduling but omits queues, request timeouts,
retry identity, flow control, and concurrent term changes. Those concerns
belong around the deterministic state machine rather than inside it.

## Fixed membership versus reconfiguration

A fixed odd replica set makes majority commitment unambiguous. Real clusters
need joint consensus (or an equivalently safe reconfiguration protocol) so old
and new memberships overlap during transition. Reusing diagnostic ISR as
membership is compact but unsafe.

## CRC32 versus stronger integrity

CRC32 cheaply detects common storage damage and is available in the JDK. It is
not authentication and does not protect against intentional alteration. A
production format would protect header boundaries explicitly and may add
cryptographic integrity at another layer.

## Repair versus evidence preservation

Automatically repairing only a provably incomplete final suffix improves crash
recovery. Refusing to discard complete corruption can reduce availability, but
it preserves evidence and avoids silently accepting a shorter history. An
operator-controlled repair tool can make the availability decision with an
audit trail.
