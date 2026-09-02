package edu.learningfactory.minilog;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** A single-partition append-only log split into offset-named segment files. */
public final class SegmentedLog implements AutoCloseable {
    private static final Pattern SEGMENT_NAME = Pattern.compile("([0-9]{20})\\.log");

    private final Path directory;
    private final long maxSegmentBytes;
    private final int maxRecordBytes;
    private final List<StoredRecord> records;
    private final List<Segment> segments;

    private FileChannel activeChannel;
    private long nextOffset;
    private boolean closed;
    private boolean failed;

    private SegmentedLog(
            Path directory,
            long maxSegmentBytes,
            int maxRecordBytes,
            List<StoredRecord> records,
            List<Segment> segments,
            FileChannel activeChannel,
            long nextOffset) {
        this.directory = directory;
        this.maxSegmentBytes = maxSegmentBytes;
        this.maxRecordBytes = maxRecordBytes;
        this.records = records;
        this.segments = segments;
        this.activeChannel = activeChannel;
        this.nextOffset = nextOffset;
    }

    public static SegmentedLog open(
            Path directory,
            long maxSegmentBytes,
            int maxRecordBytes) throws IOException {
        Objects.requireNonNull(directory, "directory");
        if (maxSegmentBytes <= 0) {
            throw new IllegalArgumentException("maxSegmentBytes must be positive");
        }
        if (maxRecordBytes <= 0) {
            throw new IllegalArgumentException("maxRecordBytes must be positive");
        }
        Path normalized = directory.toAbsolutePath().normalize();
        Files.createDirectories(normalized);
        if (!Files.isDirectory(normalized, LinkOption.NOFOLLOW_LINKS)) {
            throw new IOException("log path is not a regular directory: " + normalized);
        }

        List<SegmentFile> files = discoverSegments(normalized);
        if (files.isEmpty()) {
            Path initial = normalized.resolve(segmentName(0));
            Files.createFile(initial);
            files.add(new SegmentFile(0, initial));
        }

        List<StoredRecord> recoveredRecords = new ArrayList<>();
        List<Segment> recoveredSegments = new ArrayList<>();
        long expectedOffset = 0;
        for (int index = 0; index < files.size(); index++) {
            SegmentFile file = files.get(index);
            boolean finalSegment = index == files.size() - 1;
            if (file.baseOffset() != expectedOffset) {
                throw new CorruptLogException(
                        "segment base " + file.baseOffset() + " does not equal expected offset "
                                + expectedOffset);
            }

            long position = 0;
            int recordsInSegment = 0;
            try (FileChannel channel = FileChannel.open(
                    file.path(), StandardOpenOption.READ, StandardOpenOption.WRITE)) {
                while (true) {
                    RecordCodec.DecodeResult decoded =
                            RecordCodec.decode(channel, position, maxRecordBytes);
                    if (decoded.status() == RecordCodec.Status.CLEAN_EOF) {
                        break;
                    }
                    if (decoded.status() == RecordCodec.Status.TORN_TAIL) {
                        if (!finalSegment) {
                            throw new CorruptLogException(
                                    "incomplete frame in non-final segment " + file.path().getFileName());
                        }
                        channel.truncate(position);
                        channel.force(true);
                        break;
                    }
                    LogRecord record = decoded.record();
                    if (record.offset() != expectedOffset) {
                        throw new CorruptLogException(
                                "record offset " + record.offset() + " does not equal expected offset "
                                        + expectedOffset);
                    }
                    recoveredRecords.add(new StoredRecord(record, decoded.encodedBytes()));
                    expectedOffset++;
                    recordsInSegment++;
                    position = decoded.nextPosition();
                }
                position = channel.size();
            }
            if (!finalSegment && recordsInSegment == 0) {
                throw new CorruptLogException("non-final segment is empty: " + file.path().getFileName());
            }
            recoveredSegments.add(new Segment(file.baseOffset(), file.path(), position));
        }

        Segment active = recoveredSegments.get(recoveredSegments.size() - 1);
        FileChannel activeChannel = FileChannel.open(active.path(), StandardOpenOption.WRITE);
        activeChannel.position(active.sizeBytes());
        return new SegmentedLog(
                normalized,
                maxSegmentBytes,
                maxRecordBytes,
                recoveredRecords,
                recoveredSegments,
                activeChannel,
                expectedOffset);
    }

    private static List<SegmentFile> discoverSegments(Path directory) throws IOException {
        List<SegmentFile> result = new ArrayList<>();
        try (DirectoryStream<Path> entries = Files.newDirectoryStream(directory)) {
            for (Path entry : entries) {
                String name = entry.getFileName().toString();
                if (!name.endsWith(".log")) {
                    continue;
                }
                Matcher matcher = SEGMENT_NAME.matcher(name);
                if (!matcher.matches()) {
                    throw new CorruptLogException("invalid segment name: " + name);
                }
                if (!Files.isRegularFile(entry, LinkOption.NOFOLLOW_LINKS)) {
                    throw new CorruptLogException("segment is not a regular file: " + name);
                }
                long base;
                try {
                    base = Long.parseLong(matcher.group(1));
                } catch (NumberFormatException exception) {
                    throw new CorruptLogException("segment base offset is out of range: " + name, exception);
                }
                result.add(new SegmentFile(base, entry));
            }
        }
        result.sort(Comparator.comparingLong(SegmentFile::baseOffset));
        return result;
    }

    private static String segmentName(long baseOffset) {
        return String.format(Locale.ROOT, "%020d.log", baseOffset);
    }

    public synchronized LogRecord append(long timestampMillis, byte[] key, byte[] value)
            throws IOException {
        return append(timestampMillis, key, value, false);
    }

    public synchronized LogRecord append(
            long timestampMillis,
            byte[] key,
            byte[] value,
            boolean force) throws IOException {
        ensureUsable();
        LogRecord record = new LogRecord(nextOffset, timestampMillis, key, value);
        ByteBuffer frame = RecordCodec.encode(record, maxRecordBytes);
        int encodedBytes = frame.remaining();
        Segment active = segments.get(segments.size() - 1);
        if (active.sizeBytes() > 0 && exceedsLimit(active.sizeBytes(), encodedBytes)) {
            rotate();
            active = segments.get(segments.size() - 1);
        }

        try {
            writeFully(activeChannel, frame);
            if (force) {
                activeChannel.force(true);
            }
        } catch (IOException exception) {
            failed = true;
            try {
                activeChannel.close();
            } catch (IOException closeFailure) {
                exception.addSuppressed(closeFailure);
            }
            throw exception;
        }

        active.setSizeBytes(active.sizeBytes() + encodedBytes);
        records.add(new StoredRecord(record, encodedBytes));
        nextOffset++;
        return record;
    }

    private boolean exceedsLimit(long currentBytes, int appendedBytes) {
        return currentBytes > maxSegmentBytes - Math.min(maxSegmentBytes, (long) appendedBytes)
                || currentBytes + appendedBytes > maxSegmentBytes;
    }

    private void rotate() throws IOException {
        try {
            activeChannel.close();
            Path path = directory.resolve(segmentName(nextOffset));
            Files.createFile(path);
            activeChannel = FileChannel.open(path, StandardOpenOption.WRITE);
            segments.add(new Segment(nextOffset, path, 0));
        } catch (IOException exception) {
            failed = true;
            throw exception;
        }
    }

    private static void writeFully(FileChannel channel, ByteBuffer source) throws IOException {
        int zeroWrites = 0;
        while (source.hasRemaining()) {
            int written = channel.write(source);
            if (written == 0) {
                zeroWrites++;
                if (zeroWrites > 8) {
                    throw new IOException("file channel made no write progress");
                }
            } else {
                zeroWrites = 0;
            }
        }
    }

    public synchronized List<LogRecord> read(long startOffset, int maxRecords, int maxBytes)
            throws IOException {
        ensureUsable();
        if (startOffset < 0) {
            throw new IllegalArgumentException("startOffset must be non-negative");
        }
        if (maxRecords <= 0) {
            throw new IllegalArgumentException("maxRecords must be positive");
        }
        if (maxBytes <= 0) {
            throw new IllegalArgumentException("maxBytes must be positive");
        }
        List<LogRecord> result = new ArrayList<>();
        int bytes = 0;
        for (StoredRecord stored : records) {
            if (stored.record().offset() < startOffset) {
                continue;
            }
            if (result.size() == maxRecords || stored.encodedBytes() > maxBytes - bytes) {
                break;
            }
            result.add(stored.record());
            bytes += stored.encodedBytes();
        }
        return List.copyOf(result);
    }

    public synchronized long endOffset() {
        ensureUsable();
        return nextOffset;
    }

    public synchronized int segmentCount() {
        ensureUsable();
        return segments.size();
    }

    private void ensureUsable() {
        if (closed) {
            throw new IllegalStateException("log is closed");
        }
        if (failed) {
            throw new IllegalStateException("log is unusable after an I/O failure");
        }
    }

    @Override
    public synchronized void close() throws IOException {
        if (closed) {
            return;
        }
        closed = true;
        activeChannel.close();
    }

    private record SegmentFile(long baseOffset, Path path) {
    }

    private record StoredRecord(LogRecord record, int encodedBytes) {
    }

    private static final class Segment {
        private final long baseOffset;
        private final Path path;
        private long sizeBytes;

        private Segment(long baseOffset, Path path, long sizeBytes) {
            this.baseOffset = baseOffset;
            this.path = path;
            this.sizeBytes = sizeBytes;
        }

        long baseOffset() {
            return baseOffset;
        }

        Path path() {
            return path;
        }

        long sizeBytes() {
            return sizeBytes;
        }

        void setSizeBytes(long sizeBytes) {
            this.sizeBytes = sizeBytes;
        }
    }
}
