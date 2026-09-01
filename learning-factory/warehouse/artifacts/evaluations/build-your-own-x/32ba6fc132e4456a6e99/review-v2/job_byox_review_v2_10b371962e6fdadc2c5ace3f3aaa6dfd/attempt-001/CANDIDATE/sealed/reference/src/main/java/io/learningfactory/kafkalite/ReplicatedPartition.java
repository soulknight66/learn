package io.learningfactory.kafkalite;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * A deterministic model of one leader/follower replicated partition.
 *
 * <p>Replication is synchronous: a successful append is copied to every
 * currently available in-sync replica.  It is committed only when the ISR
 * contains at least the configured acknowledgement quorum.  Successful
 * appends advance the high watermark atomically; failed quorum checks happen
 * before any replica log is mutated.</p>
 *
 * <p>This class deliberately models replication and failover rather than
 * networking.  Public methods are synchronized so each call is one
 * deterministic state transition.</p>
 */
public final class ReplicatedPartition {
    private final int partitionId;
    private final int minInSyncReplicas;
    private final TreeMap<Integer, Replica> replicas;
    private final TreeSet<Integer> inSyncReplicaIds;

    private Integer leaderId;
    private long highWatermark;

    public ReplicatedPartition(
            int partitionId,
            List<Integer> replicaIds,
            int minInSyncReplicas) {
        if (partitionId < 0) {
            throw new IllegalArgumentException("partitionId must be non-negative");
        }
        if (replicaIds == null) {
            throw new IllegalArgumentException("replicaIds must not be null");
        }
        if (replicaIds.isEmpty()) {
            throw new IllegalArgumentException("at least one replica is required");
        }

        TreeMap<Integer, Replica> createdReplicas = new TreeMap<>();
        for (Integer replicaId : replicaIds) {
            if (replicaId == null) {
                throw new IllegalArgumentException("replicaIds must not contain null");
            }
            if (replicaId < 0) {
                throw new IllegalArgumentException("replica IDs must be non-negative");
            }
            Replica previous = createdReplicas.put(
                    replicaId,
                    new Replica(new PartitionLog(partitionId)));
            if (previous != null) {
                throw new IllegalArgumentException("duplicate replica ID: " + replicaId);
            }
        }
        if (minInSyncReplicas < 1 || minInSyncReplicas > createdReplicas.size()) {
            throw new IllegalArgumentException(
                    "minInSyncReplicas must be between 1 and the replica count");
        }

        this.partitionId = partitionId;
        this.minInSyncReplicas = minInSyncReplicas;
        this.replicas = createdReplicas;
        this.inSyncReplicaIds = new TreeSet<>(createdReplicas.keySet());
        this.leaderId = createdReplicas.firstKey();
        this.highWatermark = 0;
    }

    public int partitionId() {
        return partitionId;
    }

    /** Returns the current leader, or throws when no eligible replica exists. */
    public synchronized int leaderId() {
        return requireLeaderId();
    }

    /** Returns the exclusive end of the committed prefix. */
    public synchronized long highWatermark() {
        return highWatermark;
    }

    /** Returns a sorted, immutable snapshot of the current ISR. */
    public synchronized Set<Integer> inSyncReplicaIds() {
        return Collections.unmodifiableSet(new LinkedHashSet<>(inSyncReplicaIds));
    }

    /**
     * Appends and commits one record.
     *
     * @throws IllegalStateException if there is no leader or the ISR is below
     *         the configured acknowledgement quorum
     */
    public synchronized long append(byte[] value) {
        if (value == null) {
            throw new IllegalArgumentException("value must not be null");
        }
        byte[] valueSnapshot = value.clone();
        int currentLeaderId = requireLeaderId();
        if (inSyncReplicaIds.size() < minInSyncReplicas) {
            throw new IllegalStateException(
                    "not enough in-sync replicas: required " + minInSyncReplicas
                            + ", available " + inSyncReplicaIds.size());
        }

        Replica leader = replicas.get(currentLeaderId);
        long expectedOffset = leader.log.endOffset();
        if (expectedOffset != highWatermark) {
            throw new IllegalStateException("leader is not at the committed high watermark");
        }

        // All validation above is complete before the first mutation.  Every
        // ISR log has the same end offset by invariant, and PartitionLog.append
        // cannot fail for this already validated payload.
        for (int replicaId : inSyncReplicaIds) {
            Replica replica = replicas.get(replicaId);
            if (!replica.available) {
                throw new IllegalStateException("unavailable replica remained in ISR");
            }
            if (replica.log.endOffset() != expectedOffset) {
                throw new IllegalStateException("ISR logs have diverged");
            }
        }
        for (int replicaId : inSyncReplicaIds) {
            long appendedOffset = replicas.get(replicaId).log.append(valueSnapshot);
            if (appendedOffset != expectedOffset) {
                throw new IllegalStateException("replica assigned an unexpected offset");
            }
        }
        highWatermark = expectedOffset + 1;
        return expectedOffset;
    }

    /**
     * Reads only committed records from the current leader, beginning at an
     * inclusive consumer offset.
     */
    public synchronized List<LogRecord> read(long offset, int maxRecords) {
        PartitionLog.validateReadArguments(offset, maxRecords);
        if (offset > highWatermark) {
            throw new IllegalArgumentException("offset must not exceed highWatermark");
        }
        if (maxRecords == 0 || offset == highWatermark) {
            return List.of();
        }

        int currentLeaderId = requireLeaderId();
        long remainingCommitted = highWatermark - offset;
        int committedLimit = (int) Math.min((long) maxRecords, remainingCommitted);
        return replicas.get(currentLeaderId).log.read(offset, committedLimit);
    }

    /**
     * Marks a replica unavailable.  Its log is retained.  If it was the
     * leader, the lowest-ID available replica containing the committed prefix
     * is elected.
     */
    public synchronized void failReplica(int replicaId) {
        Replica replica = requireReplica(replicaId);
        if (!replica.available) {
            return;
        }

        replica.available = false;
        inSyncReplicaIds.remove(replicaId);
        if (leaderId != null && leaderId == replicaId) {
            leaderId = null;
            electLowestEligibleLeader();
        }
    }

    /**
     * Makes a failed replica available.  With a leader present, the retained
     * log is caught up through the committed high watermark before rejoining
     * the ISR.  When the cluster has no leader, a recovered replica that
     * already contains the committed prefix can seed a new election.
     */
    public synchronized void recoverReplica(int replicaId) {
        Replica recovering = requireReplica(replicaId);
        if (recovering.available && inSyncReplicaIds.contains(replicaId)) {
            return;
        }
        recovering.available = true;

        if (leaderId == null) {
            if (recovering.log.endOffset() == highWatermark) {
                inSyncReplicaIds.add(replicaId);
            }
            electLowestEligibleLeader();
            if (leaderId != null) {
                catchUpAllAvailableReplicas();
            }
            return;
        }

        catchUpReplica(replicaId);
    }

    public synchronized boolean isReplicaAvailable(int replicaId) {
        return requireReplica(replicaId).available;
    }

    /** Returns the durable exclusive end offset, including for failed replicas. */
    public synchronized long replicaEndOffset(int replicaId) {
        return requireReplica(replicaId).log.endOffset();
    }

    private int requireLeaderId() {
        if (leaderId == null) {
            throw new IllegalStateException("partition has no eligible leader");
        }
        Replica leader = replicas.get(leaderId);
        if (!leader.available || !inSyncReplicaIds.contains(leaderId)) {
            throw new IllegalStateException("partition leader is not in sync and available");
        }
        return leaderId;
    }

    private Replica requireReplica(int replicaId) {
        Replica replica = replicas.get(replicaId);
        if (replica == null) {
            throw new IllegalArgumentException("unknown replica ID: " + replicaId);
        }
        return replica;
    }

    private void electLowestEligibleLeader() {
        if (leaderId != null) {
            return;
        }
        for (Map.Entry<Integer, Replica> entry : replicas.entrySet()) {
            int candidateId = entry.getKey();
            Replica candidate = entry.getValue();
            if (candidate.available
                    && inSyncReplicaIds.contains(candidateId)
                    && candidate.log.endOffset() == highWatermark) {
                leaderId = candidateId;
                return;
            }
        }
    }

    private void catchUpAllAvailableReplicas() {
        if (leaderId == null) {
            return;
        }
        // Snapshot the IDs because catchUpReplica mutates the ISR set.
        for (int replicaId : new ArrayList<>(replicas.keySet())) {
            if (replicaId != leaderId && replicas.get(replicaId).available) {
                catchUpReplica(replicaId);
            }
        }
    }

    private void catchUpReplica(int replicaId) {
        int currentLeaderId = requireLeaderId();
        if (replicaId == currentLeaderId) {
            inSyncReplicaIds.add(replicaId);
            return;
        }

        Replica leader = replicas.get(currentLeaderId);
        Replica follower = replicas.get(replicaId);
        if (!follower.available) {
            throw new IllegalStateException("cannot catch up an unavailable replica");
        }
        long followerEnd = follower.log.endOffset();
        if (followerEnd > highWatermark) {
            throw new IllegalStateException("replica has data beyond the committed high watermark");
        }

        List<LogRecord> missing = leader.log.read(
                followerEnd,
                Math.toIntExact(highWatermark - followerEnd));
        for (LogRecord record : missing) {
            long appendedOffset = follower.log.append(record.value());
            if (appendedOffset != record.offset()) {
                throw new IllegalStateException("replica catch-up produced a non-contiguous offset");
            }
        }
        if (follower.log.endOffset() != highWatermark) {
            throw new IllegalStateException("replica did not reach the high watermark");
        }
        inSyncReplicaIds.add(replicaId);
    }

    private static final class Replica {
        private final PartitionLog log;
        private boolean available = true;

        private Replica(PartitionLog log) {
            this.log = log;
        }
    }
}
