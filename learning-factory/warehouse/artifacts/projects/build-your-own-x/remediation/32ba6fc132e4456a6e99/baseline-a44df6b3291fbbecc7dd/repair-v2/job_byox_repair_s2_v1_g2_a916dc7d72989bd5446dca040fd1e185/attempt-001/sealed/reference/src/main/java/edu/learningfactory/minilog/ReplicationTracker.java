package edu.learningfactory.minilog;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;

/** Leader-local tracking of replicated prefixes and majority commitment. */
public final class ReplicationTracker {
    public enum AckStatus {
        ACCEPTED,
        STALE_TERM,
        STALE_POSITION
    }

    public record Snapshot(
            long leaderTerm,
            long leaderEndOffset,
            long highWatermark,
            Map<String, Long> endOffsets,
            Set<String> inSyncReplicas) {
        public Snapshot {
            endOffsets = Map.copyOf(endOffsets);
            inSyncReplicas = Set.copyOf(inSyncReplicas);
        }
    }

    private final Set<String> replicaIds;
    private final String leaderId;
    private final long leaderTerm;
    private final long maxLagRecords;
    private final long maxSilenceMillis;
    private final Map<String, ReplicaProgress> progress;
    private final int majority;

    private long leaderEndOffset;
    private long highWatermark;
    private Object mutationOwner;

    public ReplicationTracker(
            Set<String> replicaIds,
            String leaderId,
            long leaderTerm,
            long initialLeaderEndOffset,
            long maxLagRecords,
            long maxSilenceMillis,
            long nowMillis) {
        Objects.requireNonNull(replicaIds, "replicaIds");
        Objects.requireNonNull(leaderId, "leaderId");
        if (leaderId.isBlank()) {
            throw new IllegalArgumentException("leaderId must not be blank");
        }
        if (leaderTerm < 0 || initialLeaderEndOffset < 0
                || maxLagRecords < 0 || maxSilenceMillis < 0 || nowMillis < 0) {
            throw new IllegalArgumentException("terms, offsets, limits, and time must be non-negative");
        }
        if (replicaIds.size() < 3 || replicaIds.size() % 2 == 0) {
            throw new IllegalArgumentException("replicaIds must contain an odd number of at least three IDs");
        }

        TreeSet<String> orderedIds = new TreeSet<>();
        for (String replicaId : replicaIds) {
            Objects.requireNonNull(replicaId, "replicaId");
            if (replicaId.isBlank()) {
                throw new IllegalArgumentException("replica IDs must not be blank");
            }
            orderedIds.add(replicaId);
        }
        if (orderedIds.size() != replicaIds.size()) {
            throw new IllegalArgumentException("replica IDs must be unique");
        }
        if (!orderedIds.contains(leaderId)) {
            throw new IllegalArgumentException("replicaIds must contain leaderId");
        }

        this.replicaIds = Set.copyOf(orderedIds);
        this.leaderId = leaderId;
        this.leaderTerm = leaderTerm;
        this.leaderEndOffset = initialLeaderEndOffset;
        this.maxLagRecords = maxLagRecords;
        this.maxSilenceMillis = maxSilenceMillis;
        this.majority = replicaIds.size() / 2 + 1;
        this.progress = new LinkedHashMap<>();
        for (String replicaId : orderedIds) {
            long endOffset = replicaId.equals(leaderId) ? initialLeaderEndOffset : 0;
            progress.put(replicaId, new ReplicaProgress(endOffset, nowMillis));
        }
        recomputeHighWatermark();
    }

    public synchronized void advanceLeaderEndOffset(long newEndOffset) {
        advanceLeaderEndOffsetInternal(null, newEndOffset);
    }

    synchronized void advanceLeaderEndOffsetOwned(Object owner, long newEndOffset) {
        advanceLeaderEndOffsetInternal(owner, newEndOffset);
    }

    private void advanceLeaderEndOffsetInternal(Object owner, long newEndOffset) {
        requireMutationAccess(owner);
        if (newEndOffset < leaderEndOffset) {
            throw new IllegalArgumentException("leader end offset must not regress");
        }
        leaderEndOffset = newEndOffset;
        progress.get(leaderId).endOffset = newEndOffset;
        recomputeHighWatermark();
    }

    public synchronized AckStatus acknowledge(
            String replicaId,
            long messageTerm,
            long replicatedEndOffset,
            long nowMillis) {
        return acknowledgeInternal(null, replicaId, messageTerm, replicatedEndOffset, nowMillis);
    }

    synchronized AckStatus acknowledgeOwned(
            Object owner,
            String replicaId,
            long messageTerm,
            long replicatedEndOffset,
            long nowMillis) {
        return acknowledgeInternal(owner, replicaId, messageTerm, replicatedEndOffset, nowMillis);
    }

    private AckStatus acknowledgeInternal(
            Object owner,
            String replicaId,
            long messageTerm,
            long replicatedEndOffset,
            long nowMillis) {
        requireMutationAccess(owner);
        Objects.requireNonNull(replicaId, "replicaId");
        ReplicaProgress replica = progress.get(replicaId);
        if (replica == null) {
            throw new IllegalArgumentException("unknown replica: " + replicaId);
        }
        if (replicaId.equals(leaderId)) {
            throw new IllegalArgumentException("leader progress advances through append, not acknowledgement");
        }
        if (messageTerm < 0 || replicatedEndOffset < 0 || nowMillis < 0) {
            throw new IllegalArgumentException("term, end offset, and time must be non-negative");
        }
        if (messageTerm > leaderTerm) {
            throw new IllegalStateException("acknowledgement has a future leader term");
        }
        if (messageTerm < leaderTerm) {
            return AckStatus.STALE_TERM;
        }
        if (replicatedEndOffset > leaderEndOffset) {
            throw new IllegalArgumentException("replica end offset exceeds leader end offset");
        }
        if (nowMillis < replica.lastContactMillis) {
            throw new IllegalArgumentException("replica contact time must not regress");
        }
        replica.lastContactMillis = nowMillis;
        if (replicatedEndOffset < replica.endOffset) {
            return AckStatus.STALE_POSITION;
        }
        replica.endOffset = replicatedEndOffset;
        recomputeHighWatermark();
        return AckStatus.ACCEPTED;
    }

    synchronized void claimMutationOwnership(Object owner) {
        Objects.requireNonNull(owner, "owner");
        if (mutationOwner != null) {
            throw new IllegalStateException("replication tracker already belongs to a partition");
        }
        mutationOwner = owner;
    }

    synchronized void releaseMutationOwnership(Object owner) {
        Objects.requireNonNull(owner, "owner");
        if (mutationOwner != owner) {
            throw new IllegalStateException(
                    "only the current partition may release the replication tracker");
        }
        mutationOwner = null;
    }

    private void requireMutationAccess(Object owner) {
        if (mutationOwner != owner) {
            throw new IllegalStateException(
                    "replication mutations must flow through its partition");
        }
    }

    private void recomputeHighWatermark() {
        List<Long> positions = new ArrayList<>(progress.size());
        for (ReplicaProgress replica : progress.values()) {
            positions.add(replica.endOffset);
        }
        positions.sort(java.util.Comparator.reverseOrder());
        long majorityPosition = positions.get(majority - 1);
        if (majorityPosition > highWatermark) {
            highWatermark = majorityPosition;
        }
        if (highWatermark > leaderEndOffset) {
            throw new IllegalStateException("high watermark exceeds leader end offset");
        }
    }

    public synchronized Snapshot snapshot(long nowMillis) {
        if (nowMillis < 0) {
            throw new IllegalArgumentException("nowMillis must be non-negative");
        }
        Map<String, Long> endOffsets = new LinkedHashMap<>();
        Set<String> inSync = new LinkedHashSet<>();
        for (String replicaId : new TreeSet<>(replicaIds)) {
            ReplicaProgress replica = progress.get(replicaId);
            endOffsets.put(replicaId, replica.endOffset);
            if (replicaId.equals(leaderId)) {
                inSync.add(replicaId);
                continue;
            }
            if (nowMillis < replica.lastContactMillis) {
                throw new IllegalArgumentException("snapshot time precedes a replica contact");
            }
            long lag = leaderEndOffset - replica.endOffset;
            long silence = nowMillis - replica.lastContactMillis;
            if (lag <= maxLagRecords && silence <= maxSilenceMillis) {
                inSync.add(replicaId);
            }
        }
        return new Snapshot(leaderTerm, leaderEndOffset, highWatermark, endOffsets, inSync);
    }

    public synchronized long leaderTerm() {
        return leaderTerm;
    }

    public synchronized long leaderEndOffset() {
        return leaderEndOffset;
    }

    public synchronized long highWatermark() {
        return highWatermark;
    }

    public synchronized boolean isCommitted(long recordOffset) {
        if (recordOffset < 0) {
            throw new IllegalArgumentException("recordOffset must be non-negative");
        }
        return recordOffset < highWatermark;
    }

    private static final class ReplicaProgress {
        private long endOffset;
        private long lastContactMillis;

        private ReplicaProgress(long endOffset, long lastContactMillis) {
            this.endOffset = endOffset;
            this.lastContactMillis = lastContactMillis;
        }
    }
}
