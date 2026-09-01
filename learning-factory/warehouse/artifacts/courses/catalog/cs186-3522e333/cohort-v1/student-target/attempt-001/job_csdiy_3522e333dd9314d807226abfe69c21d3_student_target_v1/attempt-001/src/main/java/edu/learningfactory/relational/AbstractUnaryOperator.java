package edu.learningfactory.relational;

/** Shared exclusive child ownership for unary operators. */
abstract class AbstractUnaryOperator extends AbstractOperator {
    private final Operator child;
    private final Schema childSchema;
    private boolean childOpened;
    private boolean childClosed;

    AbstractUnaryOperator(Operator child, Schema outputSchema) {
        super(outputSchema);
        if (child == null) {
            throw new OperatorArgumentException("child operator must not be null");
        }
        Schema declaredChildSchema = child.outputSchema();
        if (declaredChildSchema == null) {
            throw new OperatorArgumentException("child output schema must not be null");
        }
        this.child = child;
        this.childSchema = declaredChildSchema;
    }

    static Schema schemaOf(Operator child) {
        if (child == null) {
            throw new OperatorArgumentException("child operator must not be null");
        }
        Schema schema = child.outputSchema();
        if (schema == null) {
            throw new OperatorArgumentException("child output schema must not be null");
        }
        return schema;
    }

    final Schema childSchema() {
        return childSchema;
    }

    @Override
    protected final void onOpen() {
        // Mark the attempt first so the parent's failed-open rollback will ask even a custom child
        // that throws partway through open to clean up. AbstractOperator children have already made
        // their own failed open terminal, so that extra close is an idempotent no-op for them.
        childOpened = true;
        child.open();
    }

    final PullResult pullChild() {
        PullResult result = child.pull();
        if (result == null) {
            throw new RowValidationException("child returned a null pull result");
        }
        if (!result.isEndOfStream() && !childSchema.equals(result.row().schema())) {
            throw new RowValidationException(
                    "child row schema does not match its declared output schema");
        }
        return result;
    }

    @Override
    protected final void onClose() {
        if (childOpened && !childClosed) {
            childClosed = true;
            child.close();
        }
    }
}
