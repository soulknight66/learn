package io.learningfactory.kafkalite;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;
import java.util.Set;

/** Dependency-free public contract checks. */
public final class ContractTests {
    private static int passed;

    private ContractTests() {
    }

    public static void main(String[] args) {
        String selection = parseSelection(args);
        if (isSelected(selection, "milestone-1")) {
            run("record snapshots its value", ContractTests::recordSnapshotsItsValue);
            run("partition assigns contiguous offsets", ContractTests::partitionAssignsOffsets);
            run("partition reads from requested offset", ContractTests::partitionReadsByOffset);
            run("partition rejects invalid requests", ContractTests::partitionRejectsInvalidRequests);
        }
        if (isSelected(selection, "milestone-2")) {
            run("replicated configuration is validated",
                    ContractTests::replicatedConfigurationIsValidated);
            run("replicated append advances commit point", ContractTests::replicatedAppendCommits);
        }
        if (isSelected(selection, "milestone-3")) {
            run("quorum loss rejects without mutation", ContractTests::quorumLossRejectsWithoutMutation);
            run("leader failover is deterministic", ContractTests::leaderFailoverIsDeterministic);
            run("all replicas unavailable means no leader", ContractTests::noAvailableLeader);
        }
        if (isSelected(selection, "milestone-4")) {
            run("recovered replica catches up", ContractTests::recoveredReplicaCatchesUp);
            run("recovered former leader does not preempt",
                    ContractTests::recoveredFormerLeaderDoesNotPreempt);
            run("all-down singleton recovers idempotently",
                    ContractTests::allDownSingletonRecoversIdempotently);
        }
        System.out.println("PASS: " + passed + " public contract cases for " + selection);
    }

    private static String parseSelection(String[] args) {
        if (args.length == 0) {
            return "all";
        }
        if (args.length == 1
                && (args[0].equals("all")
                    || args[0].equals("milestone-1")
                    || args[0].equals("milestone-2")
                    || args[0].equals("milestone-3")
                    || args[0].equals("milestone-4"))) {
            return args[0];
        }
        System.err.println(
                "usage: sh public_tests/run.sh [all|milestone-1|milestone-2|milestone-3|milestone-4]");
        System.exit(2);
        return "all";
    }

    private static boolean isSelected(String selection, String milestone) {
        return selection.equals("all") || selection.equals(milestone);
    }

    private static void recordSnapshotsItsValue() {
        byte[] source = bytes("alpha");
        LogRecord record = new LogRecord(4, source);
        source[0] = (byte) 'X';
        checkEquals(4L, record.offset(), "record offset");
        checkArrayEquals(bytes("alpha"), record.value(), "constructor must snapshot value");

        byte[] returned = record.value();
        returned[1] = (byte) 'Y';
        checkArrayEquals(bytes("alpha"), record.value(), "value() must return an isolated value");
    }

    private static void partitionAssignsOffsets() {
        PartitionLog log = new PartitionLog(7);
        checkEquals(7, log.partitionId(), "partition ID");
        checkEquals(0L, log.endOffset(), "empty end offset");
        checkEquals(0L, log.append(bytes("zero")), "first append offset");
        checkEquals(1L, log.append(bytes("one")), "second append offset");
        checkEquals(2L, log.append(bytes("two")), "third append offset");
        checkEquals(3L, log.endOffset(), "end offset after appends");
    }

    private static void partitionReadsByOffset() {
        PartitionLog log = new PartitionLog(0);
        byte[] first = bytes("first");
        log.append(first);
        first[0] = (byte) 'X';
        log.append(bytes("second"));
        log.append(bytes("third"));

        List<LogRecord> records = log.read(1, 2);
        checkEquals(2, records.size(), "bounded read size");
        checkRecord(records.get(0), 1, "second");
        checkRecord(records.get(1), 2, "third");
        checkEquals(0, log.read(3, 10).size(), "read at end");
        checkEquals(0, log.read(0, 0).size(), "zero-sized read");
        expectThrows(IllegalArgumentException.class, () -> log.read(30, 10));
        checkRecord(log.read(0, 1).get(0), 0, "first");
    }

    private static void partitionRejectsInvalidRequests() {
        expectThrows(IllegalArgumentException.class, () -> new PartitionLog(-1));
        expectThrows(IllegalArgumentException.class, () -> new LogRecord(-1, bytes("x")));
        expectThrows(IllegalArgumentException.class, () -> new LogRecord(0, null));

        PartitionLog log = new PartitionLog(0);
        expectThrows(IllegalArgumentException.class, () -> log.append(null));
        expectThrows(IllegalArgumentException.class, () -> log.read(-1, 1));
        expectThrows(IllegalArgumentException.class, () -> log.read(0, -1));
    }

    private static void replicatedConfigurationIsValidated() {
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(-1, List.of(1), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, null, 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, Arrays.asList(1, null), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(1, 1), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(-1, 2), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(1, 2), 0));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(1, 2), 3));
    }

    private static void replicatedAppendCommits() {
        ReplicatedPartition partition = new ReplicatedPartition(2, List.of(8, 2, 5), 2);
        checkEquals(2, partition.partitionId(), "replicated partition ID");
        checkEquals(2, partition.leaderId(), "initial lowest-ID leader");
        checkEquals(0L, partition.highWatermark(), "initial high watermark");
        checkEquals(Set.of(2, 5, 8), partition.inSyncReplicaIds(), "initial ISR");

        expectThrows(IllegalArgumentException.class, () -> partition.append(null));
        checkEquals(0L, partition.highWatermark(), "invalid append must not advance watermark");
        checkEquals(0L, partition.append(bytes("committed")), "replicated append offset");
        checkEquals(1L, partition.highWatermark(), "exclusive high watermark");
        checkRecord(partition.read(0, 10).get(0), 0, "committed");
        checkEquals(0, partition.read(1, 10).size(), "read at high watermark");
        checkEquals(0, partition.read(0, 0).size(), "zero-sized replicated read");
        expectThrows(IllegalArgumentException.class, () -> partition.read(2, 1));
    }

    private static void quorumLossRejectsWithoutMutation() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(1, 2, 3), 2);
        partition.append(bytes("kept"));
        expectThrows(IllegalArgumentException.class, () -> partition.failReplica(99));
        expectThrows(IllegalArgumentException.class, () -> partition.isReplicaAvailable(99));
        expectThrows(IllegalArgumentException.class, () -> partition.replicaEndOffset(99));
        checkEquals(Set.of(1, 2, 3), partition.inSyncReplicaIds(),
                "unknown replica operations must not alter ISR");
        for (int replicaId : List.of(1, 2, 3)) {
            checkEquals(1L, partition.replicaEndOffset(replicaId),
                    "replica end offset before failure");
        }
        partition.failReplica(2);
        partition.failReplica(3);

        expectThrows(IllegalStateException.class, () -> partition.append(bytes("rejected")));
        checkEquals(1L, partition.highWatermark(), "failed append must not advance watermark");
        checkEquals(1L, partition.replicaEndOffset(1), "failed append must not mutate leader");
        checkEquals(1, partition.read(0, 10).size(), "only committed record is readable");
    }

    private static void leaderFailoverIsDeterministic() {
        ReplicatedPartition partition = new ReplicatedPartition(1, List.of(10, 4, 7), 2);
        partition.append(bytes("before"));
        partition.failReplica(4);

        checkEquals(7, partition.leaderId(), "lowest eligible follower must lead");
        check(!partition.isReplicaAvailable(4), "failed leader availability");
        checkEquals(Set.of(7, 10), partition.inSyncReplicaIds(), "ISR after failover");
        checkEquals(1L, partition.append(bytes("after")), "append after failover");
        checkRecord(partition.read(1, 1).get(0), 1, "after");
        partition.failReplica(7);
        checkEquals(10, partition.leaderId(), "later election uses an eligible replica");
    }

    private static void recoveredReplicaCatchesUp() {
        ReplicatedPartition partition = new ReplicatedPartition(3, List.of(1, 2, 3), 2);
        partition.append(bytes("a"));
        expectThrows(IllegalArgumentException.class, () -> partition.recoverReplica(99));
        checkEquals(Set.of(1, 2, 3), partition.inSyncReplicaIds(),
                "unknown recovery must not alter ISR");
        partition.failReplica(3);
        partition.append(bytes("b"));
        checkEquals(1L, partition.replicaEndOffset(3), "failed replica remains behind");

        partition.recoverReplica(3);
        check(partition.isReplicaAvailable(3), "recovered replica availability");
        checkEquals(2L, partition.replicaEndOffset(3), "recovered replica end offset");
        checkEquals(Set.of(1, 2, 3), partition.inSyncReplicaIds(), "recovered ISR");
        checkEquals(1, partition.leaderId(), "recovery must not replace active leader");

        partition.failReplica(1);
        checkEquals(2, partition.leaderId(), "lowest eligible leader after later failure");
        checkEquals(2, partition.read(0, 10).size(), "committed prefix survives recovery");
        partition.failReplica(2);
        checkEquals(3, partition.leaderId(), "caught-up replica is eligible to lead");
        checkRecord(partition.read(1, 1).get(0), 1, "b");
    }

    private static void recoveredFormerLeaderDoesNotPreempt() {
        ReplicatedPartition partition = new ReplicatedPartition(1, List.of(10, 4, 7), 2);
        partition.append(bytes("before"));
        partition.failReplica(4);
        checkEquals(7, partition.leaderId(), "lowest eligible follower must lead");
        checkEquals(1L, partition.append(bytes("after")), "append after failover");

        partition.recoverReplica(4);
        checkEquals(7, partition.leaderId(), "recovery must not preempt an active leader");
        checkEquals(2L, partition.replicaEndOffset(4), "recovered former leader catches up");
        partition.failReplica(7);
        checkEquals(4, partition.leaderId(), "later election uses lowest eligible replica");
    }

    private static void allDownSingletonRecoversIdempotently() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(11), 1);
        partition.failReplica(11);
        partition.failReplica(11);
        expectThrows(IllegalStateException.class, partition::leaderId);
        expectThrows(IllegalStateException.class, () -> partition.append(bytes("x")));

        partition.recoverReplica(11);
        partition.recoverReplica(11);
        checkEquals(11, partition.leaderId(), "recovered eligible replica can lead");
    }

    private static void noAvailableLeader() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(11), 1);
        partition.failReplica(11);
        partition.failReplica(11);
        expectThrows(IllegalStateException.class, partition::leaderId);
        expectThrows(IllegalStateException.class, () -> partition.append(bytes("x")));
    }

    private static void checkRecord(LogRecord record, long offset, String value) {
        checkEquals(offset, record.offset(), "record offset");
        checkArrayEquals(bytes(value), record.value(), "record value");
    }

    private static byte[] bytes(String value) {
        return value.getBytes(StandardCharsets.UTF_8);
    }

    private static void run(String name, Runnable test) {
        try {
            test.run();
            passed++;
        } catch (Throwable error) {
            throw new AssertionError("FAILED: " + name, error);
        }
    }

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static void checkEquals(long expected, long actual, String message) {
        if (expected != actual) {
            throw new AssertionError(message + ": expected " + expected + ", got " + actual);
        }
    }

    private static void checkEquals(Object expected, Object actual, String message) {
        if (!expected.equals(actual)) {
            throw new AssertionError(message + ": expected " + expected + ", got " + actual);
        }
    }

    private static void checkArrayEquals(byte[] expected, byte[] actual, String message) {
        if (!Arrays.equals(expected, actual)) {
            throw new AssertionError(message + ": expected " + Arrays.toString(expected)
                    + ", got " + Arrays.toString(actual));
        }
    }

    private static void expectThrows(Class<? extends Throwable> expected, Runnable action) {
        try {
            action.run();
        } catch (Throwable actual) {
            if (expected.isInstance(actual)) {
                return;
            }
            throw new AssertionError("expected " + expected.getSimpleName() + ", got "
                    + actual.getClass().getSimpleName(), actual);
        }
        throw new AssertionError("expected " + expected.getSimpleName() + " to be thrown");
    }
}
