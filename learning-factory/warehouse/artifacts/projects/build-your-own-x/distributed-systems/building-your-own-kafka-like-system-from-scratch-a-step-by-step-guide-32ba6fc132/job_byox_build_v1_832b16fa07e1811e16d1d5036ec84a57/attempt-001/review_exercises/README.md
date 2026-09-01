# Code-review exercises

This exercise file contains review prompts only. If it is separately assigned to a learner, its
sealed answer key must remain hidden.

For each proposed change, write a review comment containing severity, a concrete
failure trace, the violated contract statement, and a safer alternative.

## Change 1

Replace the sorted replica map with a HashMap and elect using the first available
entry from its iterator to reduce allocations.

## Change 2

Move the minimum-ISR check below the leader append so that a future retry can
reuse work already performed by the leader.

## Change 3

Return the internal ISR set wrapped with an unmodifiable view instead of creating
a snapshot.

## Change 4

During recovery, add the replica to ISR immediately after setting available, then
copy missing records from the leader.

## Change 5

Allow replicated read to delegate its original maxRecords directly to the leader
log because the leader normally ends at the watermark.

## Change 6

When all replicas are offline, recover any one of them and reset highWatermark to
its local end so the partition becomes writable quickly.

## Change 7

Remove defensive copies and document that callers must not mutate byte arrays,
because cloning dominates a microbenchmark.

Also review the whole design for assumptions that are safe only because this is
one in-process coordinator. Identify at least three mechanisms required before
the same election logic could run on separate machines.
