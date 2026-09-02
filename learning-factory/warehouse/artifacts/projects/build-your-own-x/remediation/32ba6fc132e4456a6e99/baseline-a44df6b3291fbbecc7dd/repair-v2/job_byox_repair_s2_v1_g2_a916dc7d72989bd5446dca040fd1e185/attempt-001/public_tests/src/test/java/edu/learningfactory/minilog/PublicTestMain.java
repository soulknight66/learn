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
import java.util.Set;

/** Minimal public contract suite; no external test framework is required. */
public final class PublicTestMain {
    private PublicTestMain() {
    }

    public static void main(String[] args) throws Exception {
        List<TestCase> tests = List.of(
                new TestCase("record defensive copies", PublicTestMain::recordDefensiveCopies),
                new TestCase("codec round trip and boundary", PublicTestMain::codecRoundTrip),
                new TestCase("segmented log round trip", PublicTestMain::segmentedLogRoundTrip),
                new TestCase("election term and freshness", PublicTestMain::electionRules),
                new TestCase("majority high watermark", PublicTestMain::majorityHighWatermark),
                new TestCase("partition read isolation", PublicTestMain::partitionReadIsolation));

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
            throw new AssertionError(failures + " public test(s) failed");
        }
    }

    private static void codecRoundTrip() throws Exception {
        Path file = Files.createTempFile("minilog-public-codec-", ".log");
        try {
            LogRecord expected = new LogRecord(3, 10, new byte[0], bytes("payload"));
            ByteBuffer frame = RecordCodec.encode(expected, 64);
            int encodedBytes = frame.remaining();
            check(encodedBytes == RecordCodec.encodedSize(expected, 64), "encoded size");
            try (FileChannel channel = FileChannel.open(
                    file, StandardOpenOption.READ, StandardOpenOption.WRITE,
                    StandardOpenOption.TRUNCATE_EXISTING)) {
                while (frame.hasRemaining()) {
                    channel.write(frame);
                }
                RecordCodec.DecodeResult decoded = RecordCodec.decode(channel, 0, 64);
                check(decoded.status() == RecordCodec.Status.COMPLETE, "complete frame status");
                check(decoded.record().equals(expected), "codec round trip");
                check(decoded.nextPosition() == encodedBytes, "next frame position");
                check(RecordCodec.decode(channel, encodedBytes, 64).status()
                                == RecordCodec.Status.CLEAN_EOF,
                        "clean end-of-file boundary");
            }
            expect(IllegalArgumentException.class,
                    () -> RecordCodec.encode(
                            new LogRecord(0, 0, bytes("ab"), bytes("cd")), 3));
        } finally {
            Files.deleteIfExists(file);
        }
    }

    private static void recordDefensiveCopies() {
        byte[] key = bytes("key");
        byte[] value = bytes("value");
        LogRecord record = new LogRecord(0, 10, key, value);
        key[0] = 'X';
        value[0] = 'X';
        check(new String(record.key(), StandardCharsets.UTF_8).equals("key"), "constructor leaked key");
        check(new String(record.value(), StandardCharsets.UTF_8).equals("value"), "constructor leaked value");
        byte[] returned = record.value();
        returned[0] = 'Y';
        check(record.value()[0] == 'v', "accessor leaked value");
        check(record.equals(new LogRecord(0, 10, bytes("key"), bytes("value"))),
                "equality must compare byte content");
    }

    private static void segmentedLogRoundTrip() throws Exception {
        Path directory = Files.createTempDirectory("minilog-public-log-");
        try {
            try (SegmentedLog log = SegmentedLog.open(directory, 70, 256)) {
                check(log.append(10, null, bytes("a"), true).offset() == 0, "first offset");
                check(log.append(11, bytes("k"), bytes("bb"), true).offset() == 1, "second offset");
                check(log.append(12, null, bytes("ccc"), true).offset() == 2, "third offset");
                check(log.segmentCount() >= 2, "small segment limit should rotate");
            }
            try (SegmentedLog reopened = SegmentedLog.open(directory, 70, 256)) {
                check(reopened.endOffset() == 3, "recovered end offset");
                List<LogRecord> records = reopened.read(1, 10, 1_000);
                check(records.size() == 2, "read from offset");
                check(records.get(0).offset() == 1 && records.get(1).offset() == 2,
                        "read order");
            }
        } finally {
            deleteTree(directory);
        }
    }

    private static void electionRules() {
        ElectionState state = new ElectionState(4);
        ElectionState.VoteDecision staleLog = state.requestVote(
                new ElectionState.VoteRequest(5, "candidate-a", 3, 2), 4, 2);
        check(!staleLog.granted(), "stale log must not win a vote");
        check(state.currentTerm() == 5, "higher request term must still be observed");
        ElectionState.VoteDecision granted = state.requestVote(
                new ElectionState.VoteRequest(5, "candidate-b", 4, 2), 4, 2);
        check(granted.granted(), "up-to-date candidate should win unused vote");
        ElectionState.VoteDecision second = state.requestVote(
                new ElectionState.VoteRequest(5, "candidate-c", 5, 2), 4, 2);
        check(!second.granted() && second.reason() == ElectionState.Reason.ALREADY_VOTED,
                "one vote per term");
    }

    private static void majorityHighWatermark() {
        ReplicationTracker tracker = new ReplicationTracker(
                Set.of("broker-a", "broker-b", "broker-c"),
                "broker-a", 7, 0, 2, 50, 100);
        tracker.advanceLeaderEndOffset(3);
        check(tracker.highWatermark() == 0, "leader alone is not a majority");
        check(tracker.acknowledge("broker-b", 7, 3, 110)
                        == ReplicationTracker.AckStatus.ACCEPTED,
                "current acknowledgement");
        check(tracker.highWatermark() == 3, "two of three replicas form a majority");
        check(tracker.acknowledge("broker-c", 6, 3, 120)
                        == ReplicationTracker.AckStatus.STALE_TERM,
                "old-term acknowledgement should be fenced");
        check(tracker.snapshot(120).endOffsets().get("broker-c") == 0,
                "fenced acknowledgement mutated progress");
    }

    private static void partitionReadIsolation() throws Exception {
        Path directory = Files.createTempDirectory("minilog-public-partition-");
        try {
            SegmentedLog log = SegmentedLog.open(directory, 1_000, 256);
            ReplicationTracker tracker = new ReplicationTracker(
                    Set.of("a", "b", "c"), "a", 9, 0, 10, 1_000, 100);
            try (PartitionLeader leader = new PartitionLeader(log, tracker)) {
                leader.append(9, 10, null, bytes("one"), true);
                leader.append(9, 11, null, bytes("two"), true);
                check(leader.fetch(0, 10, 1_000, PartitionLeader.ReadIsolation.LEADER).size() == 2,
                        "leader isolation sees local suffix");
                check(leader.fetch(0, 10, 1_000, PartitionLeader.ReadIsolation.COMMITTED).isEmpty(),
                        "unreplicated suffix is not committed");
                leader.acknowledge("b", 9, 2, 110);
                check(leader.fetch(0, 10, 1_000, PartitionLeader.ReadIsolation.COMMITTED).size() == 2,
                        "majority-replicated prefix is committed");
                expect(FencedLeaderException.class,
                        () -> leader.append(8, 12, null, bytes("rejected"), true));
                check(leader.snapshot(110).leaderEndOffset() == 2, "fenced append mutated log");
            }
        } finally {
            deleteTree(directory);
        }
    }

    private static byte[] bytes(String text) {
        return text.getBytes(StandardCharsets.UTF_8);
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
