package io.learningfactory.kafkalite;

import java.util.List;
import java.util.Set;

/** A fixed replica set for one synchronously replicated partition. */
public final class ReplicatedPartition {
    public ReplicatedPartition(
            int partitionId,
            List<Integer> replicaIds,
            int minInSyncReplicas) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public int partitionId() {
        throw new UnsupportedOperationException("Not implemented");
    }

    public int leaderId() {
        throw new UnsupportedOperationException("Not implemented");
    }

    public long highWatermark() {
        throw new UnsupportedOperationException("Not implemented");
    }

    public Set<Integer> inSyncReplicaIds() {
        throw new UnsupportedOperationException("Not implemented");
    }

    public long append(byte[] value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public List<LogRecord> read(long fromOffset, int maxRecords) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public void failReplica(int replicaId) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public void recoverReplica(int replicaId) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public boolean isReplicaAvailable(int replicaId) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public long replicaEndOffset(int replicaId) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
