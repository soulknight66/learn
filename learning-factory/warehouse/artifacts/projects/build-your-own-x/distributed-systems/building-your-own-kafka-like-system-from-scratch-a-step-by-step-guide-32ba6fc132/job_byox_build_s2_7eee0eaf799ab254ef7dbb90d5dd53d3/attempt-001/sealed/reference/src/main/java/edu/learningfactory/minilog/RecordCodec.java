package edu.learningfactory.minilog;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.util.Objects;
import java.util.zip.CRC32;

/** Package-private wire-format boundary used by the log and package tests. */
final class RecordCodec {
    static final int MAGIC = 0x4d4c4f47;
    static final short VERSION = 1;
    static final int FIXED_BODY_BYTES = 32;
    static final int MIN_ENCODED_BYTES = 8 + FIXED_BODY_BYTES;

    private static final short NULL_KEY_FLAG = 1;
    private static final short KNOWN_FLAGS = NULL_KEY_FLAG;

    enum Status {
        COMPLETE,
        CLEAN_EOF,
        TORN_TAIL
    }

    record DecodeResult(
            Status status,
            LogRecord record,
            long nextPosition,
            int encodedBytes) {
        DecodeResult {
            Objects.requireNonNull(status, "status");
            if ((status == Status.COMPLETE) != (record != null)) {
                throw new IllegalArgumentException("only a complete result has a record");
            }
        }
    }

    private RecordCodec() {
    }

    static ByteBuffer encode(LogRecord record, int maxRecordBytes) {
        Objects.requireNonNull(record, "record");
        byte[] key = record.key();
        byte[] value = record.value();
        int size = checkedEncodedSize(key, value, maxRecordBytes);

        int bodySize = size - 8;
        ByteBuffer body = ByteBuffer.allocate(bodySize).order(ByteOrder.BIG_ENDIAN);
        short flags = key == null ? NULL_KEY_FLAG : 0;
        body.putInt(MAGIC);
        body.putShort(VERSION);
        body.putShort(flags);
        body.putLong(record.offset());
        body.putLong(record.timestampMillis());
        body.putInt(key == null ? -1 : key.length);
        body.putInt(value.length);
        if (key != null) {
            body.put(key);
        }
        body.put(value);

        CRC32 checksum = new CRC32();
        checksum.update(body.array());
        int frameLength = Integer.BYTES + bodySize;
        ByteBuffer frame = ByteBuffer.allocate(size).order(ByteOrder.BIG_ENDIAN);
        frame.putInt(frameLength);
        frame.putInt((int) checksum.getValue());
        frame.put(body.array());
        frame.flip();
        return frame;
    }

    static int encodedSize(LogRecord record, int maxRecordBytes) {
        Objects.requireNonNull(record, "record");
        return checkedEncodedSize(record.key(), record.value(), maxRecordBytes);
    }

    private static int checkedEncodedSize(byte[] key, byte[] value, int maxRecordBytes) {
        if (maxRecordBytes <= 0) {
            throw new IllegalArgumentException("maxRecordBytes must be positive");
        }
        if (value.length > maxRecordBytes) {
            throw new IllegalArgumentException("value exceeds maxRecordBytes");
        }
        long payloadBytes = (long) value.length + (key == null ? 0L : key.length);
        if (payloadBytes > maxRecordBytes) {
            throw new IllegalArgumentException("combined key and value exceed maxRecordBytes");
        }
        long encodedBytes = 8L + FIXED_BODY_BYTES + payloadBytes;
        if (encodedBytes > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("encoded record is too large");
        }
        return (int) encodedBytes;
    }

    static DecodeResult decode(
            FileChannel channel,
            long position,
            int maxRecordBytes) throws IOException {
        Objects.requireNonNull(channel, "channel");
        if (position < 0) {
            throw new IllegalArgumentException("position must be non-negative");
        }
        if (maxRecordBytes <= 0) {
            throw new IllegalArgumentException("maxRecordBytes must be positive");
        }

        long fileSize = channel.size();
        if (position == fileSize) {
            return new DecodeResult(Status.CLEAN_EOF, null, position, 0);
        }
        if (position > fileSize) {
            throw new IllegalArgumentException("position is beyond end of file");
        }
        long remaining = fileSize - position;
        if (remaining < Integer.BYTES) {
            return new DecodeResult(Status.TORN_TAIL, null, position, 0);
        }

        ByteBuffer lengthBuffer = ByteBuffer.allocate(Integer.BYTES).order(ByteOrder.BIG_ENDIAN);
        if (!readFully(channel, lengthBuffer, position)) {
            return new DecodeResult(Status.TORN_TAIL, null, position, 0);
        }
        lengthBuffer.flip();
        int frameLength = lengthBuffer.getInt();
        long maximumFrameLength = (long) Integer.BYTES + FIXED_BODY_BYTES + maxRecordBytes;
        if (frameLength < Integer.BYTES + FIXED_BODY_BYTES) {
            throw new CorruptLogException("frame length is below the minimum at byte " + position);
        }
        if ((long) frameLength > maximumFrameLength) {
            throw new CorruptLogException("frame length exceeds configured limit at byte " + position);
        }
        long totalBytes = Integer.BYTES + (long) frameLength;
        if (remaining < totalBytes) {
            return new DecodeResult(Status.TORN_TAIL, null, position, 0);
        }

        ByteBuffer frame = ByteBuffer.allocate(frameLength).order(ByteOrder.BIG_ENDIAN);
        if (!readFully(channel, frame, position + Integer.BYTES)) {
            return new DecodeResult(Status.TORN_TAIL, null, position, 0);
        }
        frame.flip();
        int storedChecksum = frame.getInt();
        byte[] bodyBytes = new byte[frame.remaining()];
        frame.get(bodyBytes);

        CRC32 checksum = new CRC32();
        checksum.update(bodyBytes);
        if ((int) checksum.getValue() != storedChecksum) {
            throw new CorruptLogException("CRC mismatch at byte " + position);
        }

        ByteBuffer body = ByteBuffer.wrap(bodyBytes).order(ByteOrder.BIG_ENDIAN);
        int magic = body.getInt();
        short version = body.getShort();
        short flags = body.getShort();
        long offset = body.getLong();
        long timestampMillis = body.getLong();
        int keyLength = body.getInt();
        int valueLength = body.getInt();

        if (magic != MAGIC) {
            throw new CorruptLogException("unknown frame marker at byte " + position);
        }
        if (version != VERSION) {
            throw new CorruptLogException("unsupported frame version at byte " + position);
        }
        if ((flags & ~KNOWN_FLAGS) != 0) {
            throw new CorruptLogException("unknown frame flags at byte " + position);
        }
        boolean nullKey = (flags & NULL_KEY_FLAG) != 0;
        if ((nullKey && keyLength != -1) || (!nullKey && keyLength < 0)) {
            throw new CorruptLogException("key null flag and length disagree at byte " + position);
        }
        if (valueLength < 0) {
            throw new CorruptLogException("negative value length at byte " + position);
        }
        long payloadLength = (nullKey ? 0L : keyLength) + (long) valueLength;
        if (valueLength > maxRecordBytes || payloadLength > maxRecordBytes) {
            throw new CorruptLogException("record payload exceeds configured limit at byte " + position);
        }
        if (payloadLength != body.remaining()) {
            throw new CorruptLogException("record lengths do not match frame at byte " + position);
        }

        byte[] key = null;
        if (!nullKey) {
            key = new byte[keyLength];
            body.get(key);
        }
        byte[] value = new byte[valueLength];
        body.get(value);
        try {
            LogRecord record = new LogRecord(offset, timestampMillis, key, value);
            return new DecodeResult(
                    Status.COMPLETE,
                    record,
                    position + totalBytes,
                    Math.toIntExact(totalBytes));
        } catch (IllegalArgumentException exception) {
            throw new CorruptLogException("invalid record metadata at byte " + position, exception);
        }
    }

    private static boolean readFully(FileChannel channel, ByteBuffer target, long position)
            throws IOException {
        int zeroReads = 0;
        while (target.hasRemaining()) {
            int read = channel.read(target, position + target.position());
            if (read < 0) {
                return false;
            }
            if (read == 0) {
                zeroReads++;
                if (zeroReads > 8) {
                    throw new IOException("file channel made no read progress");
                }
            } else {
                zeroReads = 0;
            }
        }
        return true;
    }
}
