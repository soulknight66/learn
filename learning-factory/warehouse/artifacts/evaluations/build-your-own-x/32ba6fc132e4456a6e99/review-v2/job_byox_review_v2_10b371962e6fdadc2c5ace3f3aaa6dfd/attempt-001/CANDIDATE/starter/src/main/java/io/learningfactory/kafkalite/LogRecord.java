package io.learningfactory.kafkalite;

/** An immutable record stored at a partition offset. */
public final class LogRecord {
    public LogRecord(long offset, byte[] value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public long offset() {
        throw new UnsupportedOperationException("Not implemented");
    }

    public byte[] value() {
        throw new UnsupportedOperationException("Not implemented");
    }
}
