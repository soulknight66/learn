package edu.learningfactory.minilog;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;

/** Package-private wire-format boundary used by the log and package tests. */
final class RecordCodec {
    static final int MAGIC = 0x4d4c4f47;
    static final short VERSION = 1;
    static final int LENGTH_HEADER_BYTES = 2 * Integer.BYTES;
    static final int FIXED_BODY_BYTES = 32;
    static final int MIN_ENCODED_BYTES = LENGTH_HEADER_BYTES + Integer.BYTES + FIXED_BODY_BYTES;

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
    }

    private RecordCodec() {
    }

    static ByteBuffer encode(LogRecord record, int maxRecordBytes) {
        throw new UnsupportedOperationException("TODO milestone 2: encode a checked frame");
    }

    static int encodedSize(LogRecord record, int maxRecordBytes) {
        throw new UnsupportedOperationException("TODO milestone 2: calculate the frame size");
    }

    static DecodeResult decode(
            FileChannel channel,
            long position,
            int maxRecordBytes) throws IOException {
        throw new UnsupportedOperationException("TODO milestone 2: decode one frame");
    }
}
