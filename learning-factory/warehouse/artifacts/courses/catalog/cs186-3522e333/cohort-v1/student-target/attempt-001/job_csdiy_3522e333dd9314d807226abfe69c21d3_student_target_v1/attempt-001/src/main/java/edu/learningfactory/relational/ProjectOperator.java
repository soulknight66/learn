package edu.learningfactory.relational;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Reorders and/or selects a nonempty set of distinct child columns. */
public final class ProjectOperator extends AbstractUnaryOperator {
    private final List<String> columnNames;
    private final int[] sourceIndexes;

    /** Takes exclusive lifecycle ownership of {@code child}. */
    public ProjectOperator(Operator child, List<String> columnNames) {
        this(child, buildPlan(child, columnNames));
    }

    /** Takes exclusive lifecycle ownership of {@code child}. */
    public ProjectOperator(Operator child, String... columnNames) {
        this(child, namesAsList(columnNames));
    }

    private ProjectOperator(Operator child, ProjectionPlan plan) {
        super(child, plan.outputSchema);
        this.columnNames = plan.columnNames;
        this.sourceIndexes = plan.sourceIndexes;
    }

    public List<String> columnNames() {
        return columnNames;
    }

    @Override
    protected PullResult onPull() {
        PullResult result = pullChild();
        if (result.isEndOfStream()) {
            return result;
        }

        Row source = result.row();
        List<Object> projected = new ArrayList<Object>(sourceIndexes.length);
        for (int sourceIndex : sourceIndexes) {
            projected.add(source.value(sourceIndex));
        }
        return PullResult.row(new Row(outputSchema(), projected));
    }

    private static List<String> namesAsList(String[] names) {
        if (names == null) {
            throw new OperatorArgumentException("projection columns must not be null");
        }
        return Arrays.asList(names);
    }

    private static ProjectionPlan buildPlan(Operator child, List<String> requestedNames) {
        Schema inputSchema = schemaOf(child);
        if (requestedNames == null) {
            throw new OperatorArgumentException("projection columns must not be null");
        }
        if (requestedNames.isEmpty()) {
            throw new OperatorArgumentException("projection must contain at least one column");
        }

        List<String> names = new ArrayList<String>(requestedNames.size());
        List<Column> columns = new ArrayList<Column>(requestedNames.size());
        int[] indexes = new int[requestedNames.size()];
        Set<String> seen = new HashSet<String>();
        for (int index = 0; index < requestedNames.size(); index++) {
            String name = requestedNames.get(index);
            if (name == null || name.trim().isEmpty()) {
                throw new OperatorArgumentException(
                        "projection column names must not be null or blank");
            }
            if (!seen.add(name)) {
                throw new OperatorArgumentException("duplicate projection column: " + name);
            }
            int sourceIndex = inputSchema.indexOf(name);
            if (sourceIndex < 0) {
                throw new OperatorArgumentException("unknown projection column: " + name);
            }
            names.add(name);
            columns.add(inputSchema.column(sourceIndex));
            indexes[index] = sourceIndex;
        }

        return new ProjectionPlan(
                Collections.unmodifiableList(names), indexes, new Schema(columns));
    }

    private static final class ProjectionPlan {
        private final List<String> columnNames;
        private final int[] sourceIndexes;
        private final Schema outputSchema;

        private ProjectionPlan(
                List<String> columnNames, int[] sourceIndexes, Schema outputSchema) {
            this.columnNames = columnNames;
            this.sourceIndexes = sourceIndexes;
            this.outputSchema = outputSchema;
        }
    }
}
