package edu.learningfactory.minilog;

import java.io.IOException;
import java.util.ArrayList;
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
        if (expectedLeaderTerm != replication.leaderTerm()) {
            throw new FencedLeaderException(
                    "append term " + expectedLeaderTerm + " does not match active term "
                            + replication.leaderTerm());
        }
        LogRecord record = log.append(timestampMillis, key, value, force);
        replication.advanceLeaderEndOffset(log.endOffset());
        return record;
    }

    public synchronized ReplicationTracker.AckStatus acknowledge(
            String replicaId,
            long messageTerm,
            long replicatedEndOffset,
            long nowMillis) {
        return replication.acknowledge(replicaId, messageTerm, replicatedEndOffset, nowMillis);
    }

    public synchronized List<LogRecord> fetch(
            long startOffset,
            int maxRecords,
            int maxBytes,
            ReadIsolation isolation) throws IOException {
        Objects.requireNonNull(isolation, "isolation");
        List<LogRecord> local = log.read(startOffset, maxRecords, maxBytes);
        if (isolation == ReadIsolation.LEADER) {
            return local;
        }
        long highWatermark = replication.highWatermark();
        List<LogRecord> committed = new ArrayList<>();
        for (LogRecord record : local) {
            if (record.offset() >= highWatermark) {
                break;
            }
            committed.add(record);
        }
        return List.copyOf(committed);
    }

    public synchronized ReplicationTracker.Snapshot snapshot(long nowMillis) {
        return replication.snapshot(nowMillis);
    }

    @Override
    public synchronized void close() throws IOException {
        log.close();
    }
}
