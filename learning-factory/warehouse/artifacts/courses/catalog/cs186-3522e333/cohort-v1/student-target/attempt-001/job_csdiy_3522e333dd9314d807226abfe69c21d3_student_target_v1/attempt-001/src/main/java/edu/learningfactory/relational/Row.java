package edu.learningfactory.relational;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** An immutable row whose values are checked against its schema. */
public final class Row {
    private final Schema schema;
    private final List<Object> values;

    public Row(Schema schema, List<?> values) {
        if (schema == null) {
            throw new RowValidationException("row schema must not be null");
        }
        if (values == null) {
            throw new RowValidationException("row values must not be null");
        }
        if (values.size() != schema.size()) {
            throw new RowValidationException(
                    "row has " + values.size() + " values for " + schema.size() + " columns");
        }

        List<Object> snapshot = new ArrayList<Object>(values.size());
        for (int index = 0; index < values.size(); index++) {
            Object value = values.get(index);
            DataType type = schema.column(index).type();
            if (!accepts(type, value)) {
                throw new RowValidationException(
                        "value for column '" + schema.column(index).name()
                                + "' must be " + javaTypeName(type));
            }
            snapshot.add(value);
        }
        this.schema = schema;
        this.values = Collections.unmodifiableList(snapshot);
    }

    public static Row of(Schema schema, Object... values) {
        if (values == null) {
            throw new RowValidationException("row values must not be null");
        }
        return new Row(schema, Arrays.asList(values));
    }

    public Schema schema() {
        return schema;
    }

    /** Returns the immutable values in schema order. */
    public List<Object> values() {
        return values;
    }

    public Object value(int index) {
        return values.get(index);
    }

    public Object value(String columnName) {
        int index = schema.indexOf(columnName);
        if (index < 0) {
            throw new SchemaException("unknown column: " + columnName);
        }
        return value(index);
    }

    private static boolean accepts(DataType type, Object value) {
        if (value == null) {
            return false;
        }
        if (type == DataType.INT) {
            return value instanceof Integer;
        }
        return value instanceof String;
    }

    private static String javaTypeName(DataType type) {
        return type == DataType.INT ? "Integer" : "String";
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof Row)) {
            return false;
        }
        Row that = (Row) other;
        return schema.equals(that.schema) && values.equals(that.values);
    }

    @Override
    public int hashCode() {
        return Objects.hash(schema, values);
    }

    @Override
    public String toString() {
        return values.toString();
    }
}
