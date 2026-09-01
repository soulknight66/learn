package io.learningfactory.kafkalite;

import java.util.Arrays;

/**
 * One immutable entry in a {@link PartitionLog}.
 *
 * <p>The payload is copied both on construction and on access.  This keeps a
 * caller from changing data which has already been appended to a log.</p>
 */
public final class LogRecord {
    private final long offset;
    private final byte[] value;

    public LogRecord(long offset, byte[] value) {
        if (offset < 0) {
            throw new IllegalArgumentException("offset must be non-negative");
        }
        if (value == null) {
            throw new IllegalArgumentException("value must not be null");
        }
        this.offset = offset;
        this.value = value.clone();
    }

    public long offset() {
        return offset;
    }

    public byte[] value() {
        return value.clone();
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof LogRecord that)) {
            return false;
        }
        return offset == that.offset && Arrays.equals(value, that.value);
    }

    @Override
    public int hashCode() {
        return 31 * Long.hashCode(offset) + Arrays.hashCode(value);
    }

    @Override
    public String toString() {
        return "LogRecord[offset=" + offset + ", valueLength=" + value.length + "]";
    }
}
