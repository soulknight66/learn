package edu.learningfactory.relational;

import java.util.NoSuchElementException;

/** The explicit result of one pull: either one row or end-of-stream. */
public final class PullResult {
    private static final PullResult END_OF_STREAM = new PullResult(null, true);

    private final Row row;
    private final boolean endOfStream;

    private PullResult(Row row, boolean endOfStream) {
        this.row = row;
        this.endOfStream = endOfStream;
    }

    public static PullResult row(Row row) {
        if (row == null) {
            throw new RowValidationException("pull result row must not be null");
        }
        return new PullResult(row, false);
    }

    public static PullResult endOfStream() {
        return END_OF_STREAM;
    }

    public boolean isEndOfStream() {
        return endOfStream;
    }

    /** Returns the row, or fails when this result denotes end-of-stream. */
    public Row row() {
        if (endOfStream) {
            throw new NoSuchElementException("end-of-stream has no row");
        }
        return row;
    }
}
