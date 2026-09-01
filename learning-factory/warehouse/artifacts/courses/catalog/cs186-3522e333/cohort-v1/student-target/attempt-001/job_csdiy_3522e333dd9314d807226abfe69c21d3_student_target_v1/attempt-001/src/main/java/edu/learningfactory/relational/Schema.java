package edu.learningfactory.relational;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/** An immutable, ordered collection of uniquely named columns. */
public final class Schema {
    private final List<Column> columns;

    public Schema(List<Column> columns) {
        if (columns == null) {
            throw new SchemaException("columns must not be null");
        }

        List<Column> snapshot = new ArrayList<Column>(columns.size());
        Set<String> names = new HashSet<String>();
        for (Column column : columns) {
            if (column == null) {
                throw new SchemaException("schema must not contain a null column");
            }
            if (!names.add(column.name())) {
                throw new SchemaException("duplicate column name: " + column.name());
            }
            snapshot.add(column);
        }
        this.columns = Collections.unmodifiableList(snapshot);
    }

    public static Schema of(Column... columns) {
        if (columns == null) {
            throw new SchemaException("columns must not be null");
        }
        return new Schema(Arrays.asList(columns));
    }

    /** Returns the immutable columns in declaration order. */
    public List<Column> columns() {
        return columns;
    }

    public int size() {
        return columns.size();
    }

    public Column column(int index) {
        return columns.get(index);
    }

    /** Returns the zero-based index, or {@code -1} when the name is absent. */
    public int indexOf(String name) {
        if (name == null) {
            return -1;
        }
        for (int index = 0; index < columns.size(); index++) {
            if (columns.get(index).name().equals(name)) {
                return index;
            }
        }
        return -1;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof Schema)) {
            return false;
        }
        Schema that = (Schema) other;
        return columns.equals(that.columns);
    }

    @Override
    public int hashCode() {
        return Objects.hash(columns);
    }

    @Override
    public String toString() {
        return columns.toString();
    }
}
