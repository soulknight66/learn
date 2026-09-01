# Debugging exercise

This exercise file contains symptoms and tasks only. If it is separately assigned to a learner, its
sealed answer key must remain hidden.

For each hypothetical defect below, identify the smallest failing trace, locate
the invariant that was broken, propose the narrowest repair, and add a regression
test. Do not weaken the contract to make a symptom disappear.

## Case A: a rejected append consumes an offset

After quorum loss, append throws IllegalStateException. Once a replica recovers,
the next successful append returns an offset one larger than expected, and one
replica has a greater end offset than the watermark.

## Case B: a consumer observes the boundary record

With highWatermark equal to 3, a read beginning at offset 2 with a large limit
occasionally returns records at offsets 2 and 3.

## Case C: failover depends on constructor order

For replica IDs [10, 4, 7], failing leader 4 elects 10 in one implementation and
7 in another. Both contain the acknowledged prefix.

## Case D: recovery makes a lagging node electable too early

A replica misses two appends. During recovery it appears in inSyncReplicaIds
before its end offset reaches the watermark. If the leader fails at that point,
the short replica can be selected.

## Case E: history changes after a successful append

A caller reuses and overwrites its byte buffer. A later read at the already
committed offset returns the new bytes, although no second append occurred.

## Case F: stale-first recovery loses liveness incorrectly

All replicas are offline and a stale replica recovers first. It correctly cannot
lead. Later an up-to-date replica recovers, but leaderId continues to fail and the
already-available stale replica is never repaired.

For every case, distinguish the root cause from downstream symptoms. State which
observations must remain unchanged when an operation fails.
