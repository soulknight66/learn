package edu.learningfactory.relational;

import java.util.Objects;

/** An immutable named, typed column. */
public final class Column {
    private final String name;
    private final DataType type;

    public Column(String name, DataType type) {
        if (name == null || name.trim().isEmpty()) {
            throw new SchemaException("column name must not be null or blank");
        }
        if (type == null) {
            throw new SchemaException("column type must not be null");
        }
        this.name = name;
        this.type = type;
    }

    public String name() {
        return name;
    }

    public DataType type() {
        return type;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof Column)) {
            return false;
        }
        Column that = (Column) other;
        return name.equals(that.name) && type == that.type;
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, type);
    }

    @Override
    public String toString() {
        return name + ":" + type;
    }
}
