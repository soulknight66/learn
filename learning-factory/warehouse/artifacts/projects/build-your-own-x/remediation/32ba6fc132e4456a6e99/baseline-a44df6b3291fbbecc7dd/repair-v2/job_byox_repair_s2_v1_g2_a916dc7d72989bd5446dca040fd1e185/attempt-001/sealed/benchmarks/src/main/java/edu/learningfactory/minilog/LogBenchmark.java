package edu.learningfactory.minilog;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Manual smoke benchmark. Its output is not generation-time validation. */
public final class LogBenchmark {
    private LogBenchmark() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("usage: LogBenchmark EMPTY_DIRECTORY RECORD_COUNT");
        }
        Path directory = Path.of(args[0]).toAbsolutePath().normalize();
        int count = Integer.parseInt(args[1]);
        if (count <= 0) {
            throw new IllegalArgumentException("RECORD_COUNT must be positive");
        }
        Files.createDirectories(directory);
        try (var entries = Files.list(directory)) {
            if (entries.findAny().isPresent()) {
                throw new IllegalArgumentException("benchmark directory must be empty");
            }
        }

        byte[] value = new byte[128];
        Arrays.fill(value, (byte) 0x5a);
        long appendStart = System.nanoTime();
        try (SegmentedLog log = SegmentedLog.open(directory, 8L * 1024 * 1024, 1024)) {
            for (int index = 0; index < count; index++) {
                log.append(index, null, value, index == count - 1);
            }
        }
        long appendNanos = System.nanoTime() - appendStart;

        long recordsRead = 0;
        long readStart = System.nanoTime();
        try (SegmentedLog log = SegmentedLog.open(directory, 8L * 1024 * 1024, 1024)) {
            while (recordsRead < log.endOffset()) {
                var batch = log.read(recordsRead, 1_000, 1_048_576);
                if (batch.isEmpty()) {
                    throw new IllegalStateException("read made no progress");
                }
                recordsRead = batch.get(batch.size() - 1).offset() + 1;
            }
        }
        long readNanos = System.nanoTime() - readStart;
        System.out.printf(
                "records=%d append_nanos=%d reopen_and_read_nanos=%d records_read=%d%n",
                count, appendNanos, readNanos, recordsRead);
    }
}
