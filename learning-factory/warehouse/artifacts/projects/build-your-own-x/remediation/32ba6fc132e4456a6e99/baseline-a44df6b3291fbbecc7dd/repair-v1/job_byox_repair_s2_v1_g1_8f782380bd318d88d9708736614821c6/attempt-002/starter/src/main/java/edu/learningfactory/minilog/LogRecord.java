package edu.learningfactory.minilog;

import java.util.Arrays;
import java.util.Objects;

/** An immutable record stored at one partition offset. */
public final class LogRecord {
    private final long offset;
    private final long timestampMillis;
    private final byte[] key;
    private final byte[] value;

    public LogRecord(long offset, long timestampMillis, byte[] key, byte[] value) {
        if (offset < 0) {
            throw new IllegalArgumentException("offset must be non-negative");
        }
        if (timestampMillis < 0) {
            throw new IllegalArgumentException("timestampMillis must be non-negative");
        }
        this.offset = offset;
        this.timestampMillis = timestampMillis;
        this.key = key == null ? null : key.clone();
        this.value = Objects.requireNonNull(value, "value").clone();
    }

    public long offset() {
        return offset;
    }

    public long timestampMillis() {
        return timestampMillis;
    }

    public byte[] key() {
        return key == null ? null : key.clone();
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
        return offset == that.offset
                && timestampMillis == that.timestampMillis
                && Arrays.equals(key, that.key)
                && Arrays.equals(value, that.value);
    }

    @Override
    public int hashCode() {
        int result = Objects.hash(offset, timestampMillis);
        result = 31 * result + Arrays.hashCode(key);
        result = 31 * result + Arrays.hashCode(value);
        return result;
    }

    @Override
    public String toString() {
        return "LogRecord[offset=" + offset + ", timestampMillis=" + timestampMillis
                + ", keyBytes=" + (key == null ? "null" : key.length)
                + ", valueBytes=" + value.length + "]";
    }
}
