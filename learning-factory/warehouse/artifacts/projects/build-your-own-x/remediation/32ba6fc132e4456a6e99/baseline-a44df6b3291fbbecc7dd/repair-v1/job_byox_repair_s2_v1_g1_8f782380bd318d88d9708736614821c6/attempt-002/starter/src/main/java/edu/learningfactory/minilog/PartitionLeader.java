package edu.learningfactory.minilog;

import java.io.IOException;
import java.util.List;
import java.util.Objects;

/** Integrates durable local storage with leader-local replication state. */
public final class PartitionLeader implements AutoCloseable {
    public enum ReadIsolation {
        LEADER,
        COMMITTED
    }

    private final SegmentedLog log;
    private final ReplicationTracker replication;

    public PartitionLeader(SegmentedLog log, ReplicationTracker replication) {
        this.log = Objects.requireNonNull(log, "log");
        this.replication = Objects.requireNonNull(replication, "replication");
        if (log.endOffset() != replication.leaderEndOffset()) {
            throw new IllegalArgumentException("log and replication end offsets must match");
        }
    }

    public synchronized LogRecord append(
            long expectedLeaderTerm,
            long timestampMillis,
            byte[] key,
            byte[] value,
            boolean force) throws IOException {
        throw new UnsupportedOperationException("TODO milestone 6: fenced append");
    }

    public synchronized ReplicationTracker.AckStatus acknowledge(
            String replicaId,
            long messageTerm,
            long replicatedEndOffset,
            long nowMillis) {
        throw new UnsupportedOperationException("TODO milestone 6: route acknowledgements");
    }

    public synchronized List<LogRecord> fetch(
            long startOffset,
            int maxRecords,
            int maxBytes,
            ReadIsolation isolation) throws IOException {
        Objects.requireNonNull(isolation, "isolation");
        throw new UnsupportedOperationException("TODO milestone 6: isolated reads");
    }

    public synchronized ReplicationTracker.Snapshot snapshot(long nowMillis) {
        return replication.snapshot(nowMillis);
    }

    @Override
    public synchronized void close() throws IOException {
        log.close();
    }
}
