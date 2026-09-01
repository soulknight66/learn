package io.learningfactory.kafkalite;

import java.util.ArrayList;
import java.util.List;

/**
 * A deterministic, append-only, in-memory partition log.
 *
 * <p>Offsets start at zero and are contiguous.  {@link #endOffset()} is the
 * exclusive next offset, so it is also the number of records currently in
 * the log.</p>
 */
public final class PartitionLog {
    private final int partitionId;
    private final ArrayList<LogRecord> records = new ArrayList<>();

    public PartitionLog(int partitionId) {
        if (partitionId < 0) {
            throw new IllegalArgumentException("partitionId must be non-negative");
        }
        this.partitionId = partitionId;
    }

    public int partitionId() {
        return partitionId;
    }

    /**
     * Appends a defensive copy of {@code value} and returns its assigned
     * offset.
     */
    public synchronized long append(byte[] value) {
        if (value == null) {
            throw new IllegalArgumentException("value must not be null");
        }
        long offset = records.size();
        records.add(new LogRecord(offset, value));
        return offset;
    }

    /** Returns the exclusive next offset. */
    public synchronized long endOffset() {
        return records.size();
    }

    /**
     * Reads in offset order, starting at {@code offset} (inclusive).
     * Reading exactly at the end returns an empty list.  An offset beyond the
     * end is invalid.  A zero limit is a valid empty read.
     */
    public synchronized List<LogRecord> read(long offset, int maxRecords) {
        validateReadArguments(offset, maxRecords);
        if (offset > records.size()) {
            throw new IllegalArgumentException("offset must not exceed endOffset");
        }
        if (maxRecords == 0 || offset == records.size()) {
            return List.of();
        }

        int fromIndex = Math.toIntExact(offset);
        int toIndex = (int) Math.min(
                (long) records.size(),
                offset + (long) maxRecords);
        return List.copyOf(records.subList(fromIndex, toIndex));
    }

    static void validateReadArguments(long offset, int maxRecords) {
        if (offset < 0) {
            throw new IllegalArgumentException("offset must be non-negative");
        }
        if (maxRecords < 0) {
            throw new IllegalArgumentException("maxRecords must be non-negative");
        }
    }
}
