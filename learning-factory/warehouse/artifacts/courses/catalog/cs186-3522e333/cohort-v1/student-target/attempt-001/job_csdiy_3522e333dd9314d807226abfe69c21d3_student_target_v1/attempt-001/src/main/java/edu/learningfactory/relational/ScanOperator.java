package edu.learningfactory.relational;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** A finite leaf operator that snapshots its input rows at construction time. */
public final class ScanOperator extends AbstractOperator {
    private final List<Row> rows;
    private int nextIndex;

    public ScanOperator(Schema schema, List<Row> rows) {
        super(requireSchema(schema));
        if (rows == null) {
            throw new OperatorArgumentException("scan rows must not be null");
        }

        List<Row> snapshot = new ArrayList<Row>(rows.size());
        for (Row row : rows) {
            if (row == null) {
                throw new RowValidationException("scan input must not contain a null row");
            }
            if (!schema.equals(row.schema())) {
                throw new RowValidationException(
                        "scan row schema does not match the scan output schema");
            }
            snapshot.add(row);
        }
        this.rows = Collections.unmodifiableList(snapshot);
    }

    /** Infers the schema from a nonempty input snapshot. */
    public ScanOperator(List<Row> rows) {
        this(inferSchema(rows), rows);
    }

    private static Schema requireSchema(Schema schema) {
        if (schema == null) {
            throw new OperatorArgumentException("scan schema must not be null");
        }
        return schema;
    }

    private static Schema inferSchema(List<Row> rows) {
        if (rows == null) {
            throw new OperatorArgumentException("scan rows must not be null");
        }
        if (rows.isEmpty()) {
            throw new OperatorArgumentException(
                    "cannot infer a scan schema from an empty input; provide a schema");
        }
        Row first = rows.get(0);
        if (first == null) {
            throw new RowValidationException("scan input must not contain a null row");
        }
        return first.schema();
    }

    @Override
    protected PullResult onPull() {
        if (nextIndex == rows.size()) {
            return PullResult.endOfStream();
        }
        return PullResult.row(rows.get(nextIndex++));
    }
}
