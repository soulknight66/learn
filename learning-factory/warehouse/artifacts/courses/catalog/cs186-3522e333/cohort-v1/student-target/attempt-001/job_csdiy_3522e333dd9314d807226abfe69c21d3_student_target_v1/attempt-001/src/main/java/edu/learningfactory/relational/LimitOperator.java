package edu.learningfactory.relational;

/** Emits at most a configured number of child rows. */
public final class LimitOperator extends AbstractUnaryOperator {
    private final long limit;
    private long emitted;

    /** Takes exclusive lifecycle ownership of {@code child}. */
    public LimitOperator(Operator child, long limit) {
        super(child, schemaOf(child));
        if (limit < 0) {
            throw new OperatorArgumentException("limit must be nonnegative");
        }
        this.limit = limit;
    }

    public long limit() {
        return limit;
    }

    @Override
    protected PullResult onPull() {
        if (emitted >= limit) {
            return PullResult.endOfStream();
        }

        PullResult result = pullChild();
        if (!result.isEndOfStream()) {
            emitted++;
        }
        return result;
    }
}
