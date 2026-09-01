package edu.learningfactory.relational;

/** A schema-bound comparison of one column with a literal. */
public final class ColumnPredicate {
    public enum Comparison {
        EQUAL,
        LESS_THAN,
        GREATER_THAN
    }

    private final Schema schema;
    private final String columnName;
    private final int columnIndex;
    private final DataType columnType;
    private final Comparison comparison;
    private final Object literal;

    public ColumnPredicate(
            Schema schema, String columnName, Comparison comparison, Object literal) {
        if (schema == null) {
            throw new PredicateValidationException("predicate schema must not be null");
        }
        if (columnName == null || columnName.trim().isEmpty()) {
            throw new PredicateValidationException("predicate column name must not be null or blank");
        }
        int index = schema.indexOf(columnName);
        if (index < 0) {
            throw new PredicateValidationException("unknown predicate column: " + columnName);
        }
        if (comparison == null) {
            throw new PredicateValidationException("comparison must not be null");
        }

        DataType type = schema.column(index).type();
        if (literal == null
                || (type == DataType.INT && !(literal instanceof Integer))
                || (type == DataType.TEXT && !(literal instanceof String))) {
            throw new PredicateValidationException(
                    "literal type does not match column '" + columnName + "'");
        }
        if (type == DataType.TEXT && comparison != Comparison.EQUAL) {
            throw new PredicateValidationException("TEXT columns support equality only");
        }

        this.schema = schema;
        this.columnName = columnName;
        this.columnIndex = index;
        this.columnType = type;
        this.comparison = comparison;
        this.literal = literal;
    }

    /** Alternate natural-language ordering for callers constructing a bound predicate. */
    public ColumnPredicate(
            String columnName, Comparison comparison, Object literal, Schema schema) {
        this(schema, columnName, comparison, literal);
    }

    public Schema schema() {
        return schema;
    }

    public String columnName() {
        return columnName;
    }

    public Comparison comparison() {
        return comparison;
    }

    public Object literal() {
        return literal;
    }

    public boolean test(Row row) {
        if (row == null) {
            throw new RowValidationException("predicate row must not be null");
        }
        if (!schema.equals(row.schema())) {
            throw new RowValidationException("predicate row has a different schema");
        }

        Object value = row.value(columnIndex);
        if (columnType == DataType.TEXT) {
            return value.equals(literal);
        }

        int ordering = Integer.compare(
                ((Integer) value).intValue(), ((Integer) literal).intValue());
        if (comparison == Comparison.EQUAL) {
            return ordering == 0;
        }
        if (comparison == Comparison.LESS_THAN) {
            return ordering < 0;
        }
        return ordering > 0;
    }
}
