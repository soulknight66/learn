package edu.learningfactory.relational;

/** Selects child rows accepted by a schema-bound predicate. */
public final class FilterOperator extends AbstractUnaryOperator {
    private final ColumnPredicate predicate;

    /** Takes exclusive lifecycle ownership of {@code child}. */
    public FilterOperator(Operator child, ColumnPredicate predicate) {
        super(child, schemaOf(child));
        if (predicate == null) {
            throw new OperatorArgumentException("filter predicate must not be null");
        }
        if (!childSchema().equals(predicate.schema())) {
            throw new PredicateValidationException(
                    "predicate schema does not match child output schema");
        }
        this.predicate = predicate;
    }

    @Override
    protected PullResult onPull() {
        while (true) {
            PullResult result = pullChild();
            if (result.isEndOfStream() || predicate.test(result.row())) {
                return result;
            }
        }
    }
}
