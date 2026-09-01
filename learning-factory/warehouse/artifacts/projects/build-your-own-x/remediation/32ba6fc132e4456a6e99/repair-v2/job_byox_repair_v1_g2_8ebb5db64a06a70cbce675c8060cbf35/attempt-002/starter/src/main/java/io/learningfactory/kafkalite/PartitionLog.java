package io.learningfactory.kafkalite;

import java.util.List;

/** An append-only log for one partition. */
public final class PartitionLog {
    public PartitionLog(int partitionId) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public int partitionId() {
        throw new UnsupportedOperationException("Not implemented");
    }

    public long append(byte[] value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public long endOffset() {
        throw new UnsupportedOperationException("Not implemented");
    }

    public List<LogRecord> read(long fromOffset, int maxRecords) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
