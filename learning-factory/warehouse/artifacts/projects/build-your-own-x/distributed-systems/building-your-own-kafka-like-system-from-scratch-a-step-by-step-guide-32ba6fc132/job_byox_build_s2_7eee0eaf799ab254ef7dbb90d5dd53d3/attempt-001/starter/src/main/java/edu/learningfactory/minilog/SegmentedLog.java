package edu.learningfactory.minilog;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/** A single-partition append-only log split into offset-named segment files. */
public final class SegmentedLog implements AutoCloseable {
    private SegmentedLog() {
    }

    public static SegmentedLog open(
            Path directory,
            long maxSegmentBytes,
            int maxRecordBytes) throws IOException {
        throw new UnsupportedOperationException("TODO milestone 3: open and recover segments");
    }

    public LogRecord append(long timestampMillis, byte[] key, byte[] value) throws IOException {
        return append(timestampMillis, key, value, false);
    }

    public LogRecord append(
            long timestampMillis,
            byte[] key,
            byte[] value,
            boolean force) throws IOException {
        throw new UnsupportedOperationException("TODO milestone 3: append and rotate");
    }

    public List<LogRecord> read(long startOffset, int maxRecords, int maxBytes) throws IOException {
        throw new UnsupportedOperationException("TODO milestone 3: bounded reads");
    }

    public long endOffset() {
        throw new UnsupportedOperationException("TODO milestone 3: expose the next offset");
    }

    public int segmentCount() {
        throw new UnsupportedOperationException("TODO milestone 3: expose segment count");
    }

    @Override
    public void close() throws IOException {
        // TODO milestone 3: make close idempotent and reject later operations.
    }
}
