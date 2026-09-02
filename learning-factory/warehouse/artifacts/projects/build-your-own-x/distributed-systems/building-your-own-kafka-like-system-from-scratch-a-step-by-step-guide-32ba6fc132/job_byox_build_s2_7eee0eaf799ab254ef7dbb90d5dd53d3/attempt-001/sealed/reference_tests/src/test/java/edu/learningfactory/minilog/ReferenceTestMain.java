package edu.learningfactory.minilog;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Evaluator-owned edge-case suite for the sealed implementation. */
public final class ReferenceTestMain {
    private ReferenceTestMain() {
    }

    public static void main(String[] args) throws Exception {
        List<TestCase> tests = List.of(
                new TestCase("codec classifies EOF and torn frames", ReferenceTestMain::codecStates),
                new TestCase("codec rejects impossible frame lengths", ReferenceTestMain::codecBounds),
                new TestCase("recovery repairs only final torn suffix", ReferenceTestMain::finalTailRepair),
                new TestCase("recovery rejects torn non-final segment", ReferenceTestMain::nonFinalTailRejected),
                new TestCase("recovery preserves CRC corruption", ReferenceTestMain::crcCorruptionPreserved),
                new TestCase("segment naming and offset continuity", ReferenceTestMain::segmentValidation),
                new TestCase("append limits reads and lifecycle", ReferenceTestMain::appendReadAndClose),
                new TestCase("election handles duplicates and new terms", ReferenceTestMain::electionEdges),
                new TestCase("replication fences and never regresses", ReferenceTestMain::replicationEdges),
                new TestCase("ISR diagnostics do not redefine quorum", ReferenceTestMain::isrIsNotQuorum),
                new TestCase("partition validates before mutation", ReferenceTestMain::partitionAtomicity));

        int failures = 0;
        for (TestCase test : tests) {
            try {
                test.body().run();
                System.out.println("PASS " + test.name());
            } catch (Throwable failure) {
                failures++;
                System.out.println("FAIL " + test.name() + " -> "
                        + failure.getClass().getSimpleName() + ": " + failure.getMessage());
                failure.printStackTrace(System.out);
            }
        }
        System.out.println("RESULT " + (tests.size() - failures) + "/" + tests.size() + " passed");
        if (failures != 0) {
            throw new AssertionError(failures + " sealed test(s) failed");
        }
    }

    private static void codecStates() throws Exception {
        Path file = Files.createTempFile("minilog-codec-", ".log");
        try {
            LogRecord expected = new LogRecord(0, 12, null, bytes("payload"));
            ByteBuffer encoded = RecordCodec.encode(expected, 128);
            int completeSize = encoded.remaining();
            try (FileChannel channel = FileChannel.open(
                    file, StandardOpenOption.READ, StandardOpenOption.WRITE,
                    StandardOpenOption.TRUNCATE_EXISTING)) {
                writeFully(channel, encoded);
                RecordCodec.DecodeResult decoded = RecordCodec.decode(channel, 0, 128);
                check(decoded.status() == RecordCodec.Status.COMPLETE, "complete status");
                check(decoded.record().equals(expected), "round-trip record");
                check(decoded.nextPosition() == completeSize, "next position");
                check(RecordCodec.decode(channel, completeSize, 128).status()
                                == RecordCodec.Status.CLEAN_EOF,
                        "clean EOF status");
                channel.truncate(completeSize - 1L);
                check(RecordCodec.decode(channel, 0, 128).status()
                                == RecordCodec.Status.TORN_TAIL,
                        "truncated frame status");
            }
        } finally {
            Files.deleteIfExists(file);
        }
    }

    private static void codecBounds() throws Exception {
        Path file = Files.createTempFile("minilog-codec-bounds-", ".log");
        try {
            try (FileChannel channel = FileChannel.open(
                    file, StandardOpenOption.READ, StandardOpenOption.WRITE,
                    StandardOpenOption.TRUNCATE_EXISTING)) {
                writeFully(channel, ByteBuffer.allocate(4).putInt(1).flip());
                expect(CorruptLogException.class, () -> RecordCodec.decode(channel, 0, 128));
            }
            expect(IllegalArgumentException.class,
                    () -> RecordCodec.encode(new LogRecord(0, 0, bytes("ab"), bytes("cd")), 3));
        } finally {
            Files.deleteIfExists(file);
        }
    }

    private static void finalTailRepair() throws Exception {
        Path directory = Files.createTempDirectory("minilog-tail-repair-");
        try {
            LogRecord first;
            int firstSize;
            try (SegmentedLog log = SegmentedLog.open(directory, 10_000, 128)) {
                first = log.append(1, null, bytes("first"), true);
                firstSize = RecordCodec.encodedSize(first, 128);
                log.append(2, null, bytes("second"), true);
            }
            Path segment = onlyLogFile(directory);
            try (FileChannel channel = FileChannel.open(segment, StandardOpenOption.WRITE)) {
                channel.truncate(channel.size() - 2);
            }
            try (SegmentedLog recovered = SegmentedLog.open(directory, 10_000, 128)) {
                check(recovered.endOffset() == 1, "torn record should not be exposed");
                check(recovered.read(0, 10, 1_000).equals(List.of(first)), "intact prefix retained");
                check(Files.size(segment) == firstSize, "tail truncated to last valid boundary");
            }
        } finally {
            deleteTree(directory);
        }
    }

    private static void nonFinalTailRejected() throws Exception {
        Path directory = Files.createTempDirectory("minilog-nonfinal-tail-");
        try {
            try (SegmentedLog log = SegmentedLog.open(directory, 41, 128)) {
                log.append(1, null, bytes("a"), true);
                log.append(2, null, bytes("b"), true);
            }
            List<Path> segments = logFiles(directory);
            check(segments.size() == 2, "test requires two segments");
            Path first = segments.get(0);
            long damagedSize = Files.size(first) - 1;
            try (FileChannel channel = FileChannel.open(first, StandardOpenOption.WRITE)) {
                channel.truncate(damagedSize);
            }
            expect(CorruptLogException.class, () -> SegmentedLog.open(directory, 41, 128));
            check(Files.size(first) == damagedSize, "non-final evidence must not be truncated again");
        } finally {
            deleteTree(directory);
        }
    }

    private static void crcCorruptionPreserved() throws Exception {
        Path directory = Files.createTempDirectory("minilog-crc-");
        try {
            try (SegmentedLog log = SegmentedLog.open(directory, 1_000, 128)) {
                log.append(1, null, bytes("durable"), true);
            }
            Path segment = onlyLogFile(directory);
            long size = Files.size(segment);
            try (FileChannel channel = FileChannel.open(
                    segment, StandardOpenOption.READ, StandardOpenOption.WRITE)) {
                ByteBuffer one = ByteBuffer.allocate(1);
                channel.read(one, size - 1);
                one.flip();
                byte changed = (byte) (one.get() ^ 0x5a);
                channel.write(ByteBuffer.wrap(new byte[] {changed}), size - 1);
                channel.force(true);
            }
            expect(CorruptLogException.class, () -> SegmentedLog.open(directory, 1_000, 128));
            check(Files.size(segment) == size, "CRC corruption must remain available as evidence");
        } finally {
            deleteTree(directory);
        }
    }

    private static void segmentValidation() throws Exception {
        Path invalidName = Files.createTempDirectory("minilog-invalid-name-");
        try {
            Files.createFile(invalidName.resolve("1.log"));
            expect(CorruptLogException.class, () -> SegmentedLog.open(invalidName, 1_000, 128));
        } finally {
            deleteTree(invalidName);
        }

        Path gap = Files.createTempDirectory("minilog-segment-gap-");
        try {
            Files.createFile(gap.resolve("00000000000000000002.log"));
            expect(CorruptLogException.class, () -> SegmentedLog.open(gap, 1_000, 128));
        } finally {
            deleteTree(gap);
        }
    }

    private static void appendReadAndClose() throws Exception {
        Path directory = Files.createTempDirectory("minilog-bounds-");
        try {
            SegmentedLog log = SegmentedLog.open(directory, 1_000, 5);
            long emptyFileSize = Files.size(onlyLogFile(directory));
            expect(IllegalArgumentException.class,
                    () -> log.append(1, bytes("abc"), bytes("def"), true));
            check(log.endOffset() == 0, "rejected append changed end offset");
            check(Files.size(onlyLogFile(directory)) == emptyFileSize,
                    "rejected append changed file");

            LogRecord first = log.append(2, null, bytes("abc"), true);
            LogRecord second = log.append(3, null, bytes("de"), true);
            int firstBytes = RecordCodec.encodedSize(first, 5);
            check(log.read(0, 10, firstBytes).equals(List.of(first)), "exact byte budget");
            check(log.read(0, 10, firstBytes - 1).isEmpty(), "undersized byte budget");
            check(log.read(0, 1, 1_000).equals(List.of(first)), "record count budget");
            check(log.read(1, 10, 1_000).equals(List.of(second)), "starting offset");
            log.close();
            log.close();
            expect(IllegalStateException.class, log::endOffset);
        } finally {
            deleteTree(directory);
        }
    }

    private static void electionEdges() {
        ElectionState state = new ElectionState(2);
        ElectionState.VoteRequest request = new ElectionState.VoteRequest(2, "a", 5, 3);
        check(state.requestVote(request, 5, 3).granted(), "first vote");
        check(state.requestVote(request, 5, 3).granted(), "idempotent repeated vote");
        check(state.requestVote(new ElectionState.VoteRequest(1, "b", 99, 99), 5, 3).reason()
                        == ElectionState.Reason.STALE_TERM,
                "lower term rejected");
        ElectionState.VoteDecision higherButStale = state.requestVote(
                new ElectionState.VoteRequest(4, "b", 4, 3), 5, 3);
        check(!higherButStale.granted() && state.currentTerm() == 4 && state.votedFor() == null,
                "new term clears vote even when log is stale");
        check(state.requestVote(new ElectionState.VoteRequest(4, "c", 0, 4), 5, 3).granted(),
                "higher last-log term is fresher");
    }

    private static void replicationEdges() throws Exception {
        ReplicationTracker tracker = new ReplicationTracker(
                Set.of("a", "b", "c"), "a", 3, 0, 10, 100, 5);
        tracker.advanceLeaderEndOffset(5);
        tracker.acknowledge("b", 3, 4, 6);
        check(tracker.highWatermark() == 4, "majority position can trail leader");
        check(tracker.acknowledge("b", 3, 3, 7)
                        == ReplicationTracker.AckStatus.STALE_POSITION,
                "old position classified");
        check(tracker.snapshot(7).endOffsets().get("b") == 4, "old position regressed progress");
        check(tracker.acknowledge("c", 2, 5, 8) == ReplicationTracker.AckStatus.STALE_TERM,
                "old term classified");
        check(tracker.snapshot(8).endOffsets().get("c") == 0, "old term mutated progress");
        expect(IllegalStateException.class, () -> tracker.acknowledge("c", 4, 0, 8));
        expect(IllegalArgumentException.class, () -> tracker.acknowledge("missing", 3, 0, 8));
        tracker.acknowledge("c", 3, 5, 9);
        check(tracker.highWatermark() == 5 && tracker.isCommitted(4), "watermark advanced");
        expect(UnsupportedOperationException.class,
                () -> tracker.snapshot(9).endOffsets().put("a", 0L));
    }

    private static void isrIsNotQuorum() {
        ReplicationTracker tracker = new ReplicationTracker(
                Set.of("a", "b", "c", "d", "e"), "a", 1, 0, 0, 100, 0);
        tracker.advanceLeaderEndOffset(4);
        tracker.acknowledge("b", 1, 4, 0);
        ReplicationTracker.Snapshot snapshot = tracker.snapshot(0);
        check(snapshot.inSyncReplicas().equals(Set.of("a", "b")), "diagnostic ISR membership");
        check(snapshot.highWatermark() == 0,
                "two replicas cannot commit in a fixed five-replica membership");
    }

    private static void partitionAtomicity() throws Exception {
        Path directory = Files.createTempDirectory("minilog-partition-atomic-");
        try {
            SegmentedLog log = SegmentedLog.open(directory, 1_000, 8);
            ReplicationTracker tracker = new ReplicationTracker(
                    Set.of("a", "b", "c"), "a", 4, 0, 10, 100, 0);
            try (PartitionLeader leader = new PartitionLeader(log, tracker)) {
                expect(FencedLeaderException.class,
                        () -> leader.append(3, 0, null, new byte[100], true));
                check(leader.snapshot(0).leaderEndOffset() == 0,
                        "term fencing happens before payload checks or mutation");
                expect(IllegalArgumentException.class,
                        () -> leader.append(4, 0, null, new byte[100], true));
                check(leader.snapshot(0).leaderEndOffset() == 0,
                        "invalid payload did not advance replication state");
            }
        } finally {
            deleteTree(directory);
        }
    }

    private static Path onlyLogFile(Path directory) throws IOException {
        List<Path> files = logFiles(directory);
        check(files.size() == 1, "expected one log file, found " + files.size());
        return files.get(0);
    }

    private static List<Path> logFiles(Path directory) throws IOException {
        try (var paths = Files.list(directory)) {
            return paths.filter(path -> path.getFileName().toString().endsWith(".log"))
                    .sorted()
                    .toList();
        }
    }

    private static void writeFully(FileChannel channel, ByteBuffer source) throws IOException {
        while (source.hasRemaining()) {
            channel.write(source);
        }
    }

    private static byte[] bytes(String value) {
        return value.getBytes(StandardCharsets.UTF_8);
    }

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static <T extends Throwable> void expect(Class<T> type, CheckedRunnable body)
            throws Exception {
        try {
            body.run();
        } catch (Throwable failure) {
            if (type.isInstance(failure)) {
                return;
            }
            throw failure;
        }
        throw new AssertionError("expected " + type.getSimpleName());
    }

    private static void deleteTree(Path root) throws IOException {
        if (!Files.exists(root)) {
            return;
        }
        try (var paths = Files.walk(root)) {
            for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) {
                Files.delete(path);
            }
        }
    }

    private record TestCase(String name, CheckedRunnable body) {
    }

    @FunctionalInterface
    private interface CheckedRunnable {
        void run() throws Exception;
    }
}
