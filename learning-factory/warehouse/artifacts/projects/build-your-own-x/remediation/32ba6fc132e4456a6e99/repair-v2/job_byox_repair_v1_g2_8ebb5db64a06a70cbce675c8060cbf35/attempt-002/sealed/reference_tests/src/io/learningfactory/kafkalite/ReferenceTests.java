package io.learningfactory.kafkalite;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/** Deterministic state and boundary checks for the sealed implementation. */
public final class ReferenceTests {
    private static int passed;

    private ReferenceTests() {
    }

    public static void main(String[] args) {
        run("record validates and isolates bytes", ReferenceTests::recordValidationAndIsolation);
        run("local log validates construction and reads", ReferenceTests::localLogBoundaries);
        run("local read results are immutable snapshots", ReferenceTests::localReadSnapshots);
        run("replica construction is validated", ReferenceTests::replicaConstructionValidation);
        run("replicated state snapshots are isolated", ReferenceTests::replicatedSnapshots);
        run("failed appends are atomic", ReferenceTests::failedAppendAtomicity);
        run("followers retain durable lag", ReferenceTests::failedFollowerRetainsLag);
        run("leader election uses lowest eligible ID", ReferenceTests::deterministicElection);
        run("all-down cluster recovers safely", ReferenceTests::allDownRecovery);
        run("stale-first recovery waits for a safe source", ReferenceTests::staleFirstRecovery);
        run("recovery and failure are idempotent", ReferenceTests::idempotentTransitions);
        run("unknown replicas do not alter state", ReferenceTests::unknownReplicaAtomicity);
        run("deterministic transition trace preserves prefix", ReferenceTests::transitionTrace);
        run("fixed-seed model trace preserves invariants", ReferenceTests::modelBasedTrace);
        System.out.println("PASS: " + passed + " sealed reference cases");
    }

    private static void recordValidationAndIsolation() {
        expectThrows(IllegalArgumentException.class, () -> new LogRecord(-1, bytes("x")));
        expectThrows(IllegalArgumentException.class, () -> new LogRecord(0, null));

        byte[] source = bytes("safe");
        LogRecord record = new LogRecord(9, source);
        source[0] = (byte) 'X';
        checkArrayEquals(bytes("safe"), record.value(), "constructor copy");
        byte[] observed = record.value();
        observed[1] = (byte) 'Y';
        checkArrayEquals(bytes("safe"), record.value(), "accessor copy");
        checkEquals(9L, record.offset(), "record offset");
    }

    private static void localLogBoundaries() {
        expectThrows(IllegalArgumentException.class, () -> new PartitionLog(-1));
        PartitionLog log = new PartitionLog(12);
        checkEquals(12, log.partitionId(), "partition ID");
        checkEquals(0, log.read(0, 0).size(), "empty zero-limit read");
        expectThrows(IllegalArgumentException.class, () -> log.read(-1, 1));
        expectThrows(IllegalArgumentException.class, () -> log.read(1, 1));
        expectThrows(IllegalArgumentException.class, () -> log.read(0, -1));
        expectThrows(IllegalArgumentException.class, () -> log.append(null));

        checkEquals(0L, log.append(bytes("zero")), "first offset");
        checkEquals(1L, log.append(bytes("one")), "second offset");
        checkEquals(2L, log.endOffset(), "exclusive end");
        checkEquals(0, log.read(2, 7).size(), "read at exclusive end");
        expectThrows(IllegalArgumentException.class, () -> log.read(3, 7));
        checkRecord(log.read(1, Integer.MAX_VALUE).get(0), 1, "one");
    }

    private static void localReadSnapshots() {
        PartitionLog log = new PartitionLog(0);
        byte[] input = bytes("original");
        log.append(input);
        input[0] = (byte) 'X';
        List<LogRecord> result = log.read(0, 1);
        expectThrows(UnsupportedOperationException.class,
                () -> result.add(new LogRecord(1, bytes("bad"))));
        byte[] returned = result.get(0).value();
        returned[0] = (byte) 'Y';
        checkRecord(log.read(0, 1).get(0), 0, "original");
    }

    private static void replicaConstructionValidation() {
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(-1, List.of(1), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, null, 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, Arrays.asList(1, null), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(-1), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(1, 1), 1));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(1, 2), 0));
        expectThrows(IllegalArgumentException.class,
                () -> new ReplicatedPartition(0, List.of(1, 2), 3));
    }

    private static void replicatedSnapshots() {
        ArrayList<Integer> ids = new ArrayList<>(List.of(9, 3, 6));
        ReplicatedPartition partition = new ReplicatedPartition(4, ids, 2);
        ids.clear();
        checkEquals(3, partition.leaderId(), "lowest initial leader");
        checkEquals(Set.of(3, 6, 9), partition.inSyncReplicaIds(), "copied IDs");
        expectThrows(UnsupportedOperationException.class,
                () -> partition.inSyncReplicaIds().remove(3));

        byte[] input = bytes("value");
        partition.append(input);
        input[0] = (byte) 'X';
        List<LogRecord> records = partition.read(0, 1);
        checkRecord(records.get(0), 0, "value");
        expectThrows(UnsupportedOperationException.class, records::clear);
        records.get(0).value()[0] = (byte) 'Y';
        checkRecord(partition.read(0, 1).get(0), 0, "value");
        checkEquals(0, partition.read(1, 0).size(), "zero-limit watermark read");
        expectThrows(IllegalArgumentException.class, () -> partition.read(2, 1));
    }

    private static void failedAppendAtomicity() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(1, 2, 3), 3);
        partition.append(bytes("kept"));
        partition.failReplica(3);
        Set<Integer> beforeIsr = partition.inSyncReplicaIds();
        expectThrows(IllegalStateException.class, () -> partition.append(bytes("rejected")));
        expectThrows(IllegalArgumentException.class, () -> partition.append(null));
        checkEquals(1L, partition.highWatermark(), "unchanged watermark");
        checkEquals(1L, partition.replicaEndOffset(1), "unchanged leader");
        checkEquals(1L, partition.replicaEndOffset(2), "unchanged follower");
        checkEquals(1L, partition.replicaEndOffset(3), "unchanged failed replica");
        checkEquals(beforeIsr, partition.inSyncReplicaIds(), "unchanged ISR");
        checkRecord(partition.read(0, 10).get(0), 0, "kept");
    }

    private static void failedFollowerRetainsLag() {
        ReplicatedPartition partition = new ReplicatedPartition(1, List.of(1, 2, 3), 2);
        partition.append(bytes("a"));
        partition.failReplica(3);
        partition.append(bytes("b"));
        partition.append(bytes("c"));
        checkEquals(1L, partition.replicaEndOffset(3), "offline durable end");
        checkEquals(3L, partition.highWatermark(), "committed end");
        checkEquals(Set.of(1, 2), partition.inSyncReplicaIds(), "lagger leaves ISR");

        partition.recoverReplica(3);
        checkEquals(3L, partition.replicaEndOffset(3), "caught-up end");
        checkEquals(Set.of(1, 2, 3), partition.inSyncReplicaIds(), "caught-up ISR");
    }

    private static void deterministicElection() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(40, 20, 30, 10), 2);
        partition.append(bytes("before"));
        checkEquals(10, partition.leaderId(), "initial election");
        partition.failReplica(10);
        checkEquals(20, partition.leaderId(), "first failover");
        partition.failReplica(20);
        checkEquals(30, partition.leaderId(), "second failover");
        partition.append(bytes("after"));
        checkEquals(2L, partition.highWatermark(), "append after failovers");
        checkEquals(Set.of(30, 40), partition.inSyncReplicaIds(), "remaining ISR");
    }

    private static void allDownRecovery() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(5, 7, 9), 2);
        partition.append(bytes("durable"));
        partition.failReplica(5);
        partition.failReplica(7);
        partition.failReplica(9);
        expectThrows(IllegalStateException.class, partition::leaderId);
        expectThrows(IllegalStateException.class, () -> partition.read(0, 1));
        checkEquals(0, partition.read(1, 10).size(), "empty boundary read needs no leader");
        checkEquals(0, partition.read(0, 0).size(), "zero-limit read needs no leader");
        expectThrows(IllegalStateException.class, () -> partition.append(bytes("no")));

        partition.recoverReplica(9);
        checkEquals(9, partition.leaderId(), "only recovered eligible leader");
        checkRecord(partition.read(0, 1).get(0), 0, "durable");
        expectThrows(IllegalStateException.class, () -> partition.append(bytes("still no quorum")));
        partition.recoverReplica(7);
        checkEquals(9, partition.leaderId(), "active leader stays stable");
        checkEquals(1L, partition.append(bytes("new")), "quorum restored");
        partition.recoverReplica(5);
        checkEquals(2L, partition.replicaEndOffset(5), "late replica catches up");
    }

    private static void staleFirstRecovery() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(1, 2, 3), 2);
        partition.append(bytes("a"));
        partition.failReplica(3);
        partition.append(bytes("b"));
        partition.failReplica(1);
        partition.failReplica(2);

        partition.recoverReplica(3);
        check(partition.isReplicaAvailable(3), "stale replica becomes available");
        checkEquals(Set.of(), partition.inSyncReplicaIds(), "stale replica stays outside ISR");
        expectThrows(IllegalStateException.class, partition::leaderId);

        partition.recoverReplica(2);
        checkEquals(2, partition.leaderId(), "up-to-date replica restores leadership");
        checkEquals(Set.of(2, 3), partition.inSyncReplicaIds(), "available laggard is repaired");
        checkEquals(2L, partition.replicaEndOffset(3), "stale replica catches up");
        checkEquals(2, partition.read(0, 10).size(), "committed history survives");
    }

    private static void idempotentTransitions() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(1, 2), 1);
        partition.append(bytes("a"));
        partition.failReplica(2);
        partition.failReplica(2);
        checkEquals(1L, partition.replicaEndOffset(2), "repeated failure keeps log");
        partition.append(bytes("b"));
        partition.recoverReplica(2);
        partition.recoverReplica(2);
        checkEquals(2L, partition.replicaEndOffset(2), "repeated recovery does not duplicate");
        checkEquals(Set.of(1, 2), partition.inSyncReplicaIds(), "repeated recovery ISR");
    }

    private static void unknownReplicaAtomicity() {
        ReplicatedPartition partition = new ReplicatedPartition(0, List.of(1, 2), 1);
        partition.append(bytes("a"));
        expectThrows(IllegalArgumentException.class, () -> partition.failReplica(99));
        expectThrows(IllegalArgumentException.class, () -> partition.recoverReplica(99));
        expectThrows(IllegalArgumentException.class, () -> partition.isReplicaAvailable(99));
        expectThrows(IllegalArgumentException.class, () -> partition.replicaEndOffset(99));
        checkEquals(1L, partition.highWatermark(), "unknown ID leaves watermark");
        checkEquals(Set.of(1, 2), partition.inSyncReplicaIds(), "unknown ID leaves ISR");
    }

    private static void transitionTrace() {
        ReplicatedPartition partition = new ReplicatedPartition(8, List.of(2, 4, 6, 8, 10), 3);
        ArrayList<String> expected = new ArrayList<>();
        appendExpected(partition, expected, "r0");
        partition.failReplica(10);
        appendExpected(partition, expected, "r1");
        partition.failReplica(8);
        appendExpected(partition, expected, "r2");
        partition.recoverReplica(10);
        partition.failReplica(2);
        appendExpected(partition, expected, "r3");
        partition.recoverReplica(8);
        partition.failReplica(4);
        appendExpected(partition, expected, "r4");
        partition.recoverReplica(2);
        partition.recoverReplica(4);

        checkEquals((long) expected.size(), partition.highWatermark(), "trace watermark");
        List<LogRecord> observed = partition.read(0, 100);
        checkEquals(expected.size(), observed.size(), "trace record count");
        for (int index = 0; index < expected.size(); index++) {
            checkRecord(observed.get(index), index, expected.get(index));
        }
        for (int replicaId : List.of(2, 4, 6, 8, 10)) {
            checkEquals((long) expected.size(), partition.replicaEndOffset(replicaId),
                    "trace replica caught up: " + replicaId);
        }
    }

    private static void modelBasedTrace() {
        List<Integer> replicaIds = List.of(2, 4, 6, 8, 10);
        ReplicatedPartition partition = new ReplicatedPartition(9, replicaIds, 3);
        TraceModel model = new TraceModel(replicaIds, 3);
        long generator = 0x4d595df4d0f33173L;

        for (int step = 0; step < 1024; step++) {
            generator = generator * 6364136223846793005L + 1442695040888963407L;
            int operation = (int) ((generator >>> 61) & 3L);
            int replicaIndex = (int) ((generator >>> 32) % replicaIds.size());
            int replicaId = replicaIds.get(replicaIndex);

            if (operation == 0) {
                String value = "model-" + step;
                if (model.canAppend()) {
                    long expectedOffset = model.append(value);
                    checkEquals(expectedOffset, partition.append(bytes(value)),
                            "model append offset at step " + step);
                } else {
                    expectThrows(IllegalStateException.class,
                            () -> partition.append(bytes(value)));
                }
            } else if (operation == 1) {
                partition.failReplica(replicaId);
                model.fail(replicaIndex);
            } else if (operation == 2) {
                partition.recoverReplica(replicaId);
                model.recover(replicaIndex);
            } else {
                long offset = (generator >>> 1) % (model.highWatermark() + 2);
                int limit = (int) ((generator >>> 17) % 7);
                checkModelRead(partition, model, offset, limit, step);
            }
            checkModelState(partition, model, step);
        }
    }

    private static void checkModelRead(
            ReplicatedPartition partition,
            TraceModel model,
            long offset,
            int limit,
            int step) {
        if (offset > model.highWatermark()) {
            expectThrows(IllegalArgumentException.class, () -> partition.read(offset, limit));
            return;
        }
        if (limit > 0 && offset < model.highWatermark() && !model.hasLeader()) {
            expectThrows(IllegalStateException.class, () -> partition.read(offset, limit));
            return;
        }

        List<LogRecord> observed = partition.read(offset, limit);
        List<String> expected = model.read(offset, limit);
        checkEquals(expected.size(), observed.size(), "model read size at step " + step);
        for (int index = 0; index < expected.size(); index++) {
            checkRecord(observed.get(index), offset + index, expected.get(index));
        }
    }

    private static void checkModelState(
            ReplicatedPartition partition,
            TraceModel model,
            int step) {
        checkEquals(model.highWatermark(), partition.highWatermark(),
                "model watermark at step " + step);
        checkEquals(model.inSyncReplicaIds(), partition.inSyncReplicaIds(),
                "model ISR at step " + step);
        for (int index = 0; index < model.replicaCount(); index++) {
            int replicaId = model.replicaId(index);
            checkEquals(model.isAvailable(index), partition.isReplicaAvailable(replicaId),
                    "model availability at step " + step + ", replica " + replicaId);
            checkEquals(model.endOffset(index), partition.replicaEndOffset(replicaId),
                    "model end offset at step " + step + ", replica " + replicaId);
        }
        if (model.hasLeader()) {
            checkEquals(model.leaderId(), partition.leaderId(),
                    "model leader at step " + step);
            checkModelRead(partition, model, 0, Integer.MAX_VALUE, step);
        } else {
            expectThrows(IllegalStateException.class, partition::leaderId);
        }
    }

    private static final class TraceModel {
        private final List<Integer> replicaIds;
        private final int minInSyncReplicas;
        private final boolean[] available;
        private final boolean[] inSync;
        private final long[] endOffsets;
        private final ArrayList<String> committed;
        private int leaderIndex;

        private TraceModel(List<Integer> replicaIds, int minInSyncReplicas) {
            this.replicaIds = List.copyOf(replicaIds);
            this.minInSyncReplicas = minInSyncReplicas;
            this.available = new boolean[replicaIds.size()];
            this.inSync = new boolean[replicaIds.size()];
            this.endOffsets = new long[replicaIds.size()];
            this.committed = new ArrayList<>();
            Arrays.fill(available, true);
            Arrays.fill(inSync, true);
            this.leaderIndex = 0;
        }

        private boolean canAppend() {
            int inSyncCount = 0;
            for (boolean member : inSync) {
                if (member) {
                    inSyncCount++;
                }
            }
            return leaderIndex >= 0 && inSyncCount >= minInSyncReplicas;
        }

        private long append(String value) {
            long offset = committed.size();
            for (int index = 0; index < inSync.length; index++) {
                if (inSync[index]) {
                    endOffsets[index]++;
                }
            }
            committed.add(value);
            return offset;
        }

        private void fail(int index) {
            if (!available[index]) {
                return;
            }
            available[index] = false;
            inSync[index] = false;
            if (leaderIndex == index) {
                leaderIndex = -1;
                elect();
            }
        }

        private void recover(int index) {
            if (available[index] && inSync[index]) {
                return;
            }
            available[index] = true;
            if (leaderIndex < 0) {
                if (endOffsets[index] == highWatermark()) {
                    inSync[index] = true;
                }
                elect();
                if (leaderIndex >= 0) {
                    for (int candidate = 0; candidate < replicaIds.size(); candidate++) {
                        if (candidate != leaderIndex && available[candidate]) {
                            catchUp(candidate);
                        }
                    }
                }
                return;
            }
            catchUp(index);
        }

        private void elect() {
            if (leaderIndex >= 0) {
                return;
            }
            for (int index = 0; index < replicaIds.size(); index++) {
                if (available[index] && inSync[index]
                        && endOffsets[index] == highWatermark()) {
                    leaderIndex = index;
                    return;
                }
            }
        }

        private void catchUp(int index) {
            if (!available[index]) {
                throw new AssertionError("model attempted to catch up an unavailable replica");
            }
            if (endOffsets[index] > highWatermark()) {
                throw new AssertionError("model replica exceeded committed history");
            }
            endOffsets[index] = highWatermark();
            inSync[index] = true;
        }

        private List<String> read(long offset, int limit) {
            int fromIndex = Math.toIntExact(offset);
            int toIndex = (int) Math.min((long) committed.size(), offset + (long) limit);
            return List.copyOf(committed.subList(fromIndex, toIndex));
        }

        private long highWatermark() {
            return committed.size();
        }

        private boolean hasLeader() {
            return leaderIndex >= 0;
        }

        private int leaderId() {
            return replicaIds.get(leaderIndex);
        }

        private Set<Integer> inSyncReplicaIds() {
            Set<Integer> result = new TreeSet<>();
            for (int index = 0; index < replicaIds.size(); index++) {
                if (inSync[index]) {
                    result.add(replicaIds.get(index));
                }
            }
            return result;
        }

        private int replicaCount() {
            return replicaIds.size();
        }

        private int replicaId(int index) {
            return replicaIds.get(index);
        }

        private boolean isAvailable(int index) {
            return available[index];
        }

        private long endOffset(int index) {
            return endOffsets[index];
        }
    }

    private static void appendExpected(
            ReplicatedPartition partition,
            List<String> expected,
            String value) {
        long offset = partition.append(bytes(value));
        checkEquals((long) expected.size(), offset, "trace append offset");
        expected.add(value);
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

    private static void checkEquals(long expected, long actual, String message) {
        if (expected != actual) {
            throw new AssertionError(message + ": expected " + expected + ", got " + actual);
        }
    }

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
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
