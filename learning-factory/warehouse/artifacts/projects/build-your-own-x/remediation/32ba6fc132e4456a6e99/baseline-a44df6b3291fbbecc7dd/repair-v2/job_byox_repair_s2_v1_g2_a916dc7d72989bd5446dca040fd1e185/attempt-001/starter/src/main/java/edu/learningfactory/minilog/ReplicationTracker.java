package edu.learningfactory.minilog;

import java.util.Map;
import java.util.Objects;
import java.util.Set;

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
        throw new UnsupportedOperationException("TODO milestone 5: initialize replica state");
    }

    public synchronized void advanceLeaderEndOffset(long newEndOffset) {
        throw new UnsupportedOperationException("TODO milestone 5: advance leader progress");
    }

    public synchronized AckStatus acknowledge(
            String replicaId,
            long messageTerm,
            long replicatedEndOffset,
            long nowMillis) {
        throw new UnsupportedOperationException("TODO milestone 5: process acknowledgements");
    }

    public synchronized Snapshot snapshot(long nowMillis) {
        throw new UnsupportedOperationException("TODO milestone 5: snapshot state");
    }

    public synchronized long leaderTerm() {
        throw new UnsupportedOperationException("TODO milestone 5: expose leader term");
    }

    public synchronized long leaderEndOffset() {
        throw new UnsupportedOperationException("TODO milestone 5: expose leader end offset");
    }

    public synchronized long highWatermark() {
        throw new UnsupportedOperationException("TODO milestone 5: expose high watermark");
    }

    public synchronized boolean isCommitted(long recordOffset) {
        throw new UnsupportedOperationException("TODO milestone 5: test committed visibility");
    }
}
