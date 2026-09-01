package edu.learningfactory.relational;

/**
 * Lifecycle implementation shared by operators.
 *
 * <p>Subclasses implement hooks only; this class owns all state transitions and stable
 * end-of-stream behavior.</p>
 */
public abstract class AbstractOperator implements Operator {
    public enum State {
        NEW,
        OPEN,
        EXHAUSTED,
        CLOSED
    }

    private final Schema outputSchema;
    private State state = State.NEW;

    protected AbstractOperator(Schema outputSchema) {
        if (outputSchema == null) {
            throw new OperatorArgumentException("output schema must not be null");
        }
        this.outputSchema = outputSchema;
    }

    @Override
    public final Schema outputSchema() {
        return outputSchema;
    }

    public final synchronized State state() {
        return state;
    }

    @Override
    public final synchronized void open() {
        if (state != State.NEW) {
            throw new LifecycleException("open requires NEW state, but was " + state);
        }
        try {
            onOpen();
            state = State.OPEN;
        } catch (RuntimeException | Error openFailure) {
            // A failed execution attempt is terminal. Give partially initialized subclasses one
            // cleanup attempt, and retain both failures without making cleanup retryable.
            state = State.CLOSED;
            try {
                onClose();
            } catch (RuntimeException | Error closeFailure) {
                if (closeFailure != openFailure) {
                    openFailure.addSuppressed(closeFailure);
                }
            }
            throw openFailure;
        }
    }

    @Override
    public final synchronized PullResult pull() {
        if (state == State.NEW) {
            throw new LifecycleException("pull requires an open operator");
        }
        if (state == State.CLOSED) {
            throw new LifecycleException("pull is not allowed after close");
        }
        if (state == State.EXHAUSTED) {
            return PullResult.endOfStream();
        }

        PullResult result = onPull();
        if (result == null) {
            throw new RowValidationException("operator returned a null pull result");
        }
        if (result.isEndOfStream()) {
            state = State.EXHAUSTED;
            return PullResult.endOfStream();
        }
        Row row = result.row();
        if (!outputSchema.equals(row.schema())) {
            throw new RowValidationException(
                    "operator row schema does not match its declared output schema");
        }
        return result;
    }

    @Override
    public final synchronized void close() {
        if (state == State.NEW) {
            throw new LifecycleException("close requires an operator that has been opened");
        }
        if (state == State.CLOSED) {
            return;
        }

        state = State.CLOSED;
        onClose();
    }

    protected void onOpen() {
        // Most leaf operators need no setup.
    }

    protected abstract PullResult onPull();

    protected void onClose() {
        // Most leaf operators own no resources.
    }
}
