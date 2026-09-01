package edu.learningfactory.relational;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.Random;

/**
 * Dependency-free executable tests for the relational pull pipeline.
 *
 * <p>Run with assertions in either state; this class uses its own assertion helpers so test
 * behavior does not depend on {@code -ea}.</p>
 */
public final class RelationalPipelineTest {
    private RelationalPipelineTest() {
    }

    public static void main(String[] args) {
        List<NamedTest> tests = Arrays.asList(
                new NamedTest("schema and row basics", RelationalPipelineTest::schemaAndRowBasics),
                new NamedTest("scan preserves stable ordering", RelationalPipelineTest::scanPreservesStableOrdering),
                new NamedTest("filter handles none, some, and all", RelationalPipelineTest::filterHandlesNoneSomeAndAll),
                new NamedTest("projection reorders values and schema", RelationalPipelineTest::projectionReordersValuesAndSchema),
                new NamedTest("limit boundary cases", RelationalPipelineTest::limitBoundaryCases),
                new NamedTest("full composed pipeline", RelationalPipelineTest::fullComposedPipeline),
                new NamedTest("validation failures are typed", RelationalPipelineTest::validationFailuresAreTyped),
                new NamedTest("operator lifecycle contract", RelationalPipelineTest::operatorLifecycleContract),
                new NamedTest("composed EOS is stable", RelationalPipelineTest::composedEndOfStreamIsStable),
                new NamedTest("failed open rolls back once", RelationalPipelineTest::failedOpenRollsBackOnce),
                new NamedTest("early close propagates exactly once", RelationalPipelineTest::earlyClosePropagatesExactlyOnce),
                new NamedTest("collection ownership and immutability", RelationalPipelineTest::collectionOwnershipAndImmutability),
                new NamedTest("fixed-seed data agrees with independent oracle", RelationalPipelineTest::fixedSeedDataAgreesWithIndependentOracle));

        int passed = 0;
        List<String> failures = new ArrayList<>();
        for (NamedTest test : tests) {
            try {
                test.body.run();
                passed++;
                System.out.println("PASS " + test.name);
            } catch (Throwable failure) {
                failures.add(test.name + ": " + failure);
                System.err.println("FAIL " + test.name + ": " + failure);
                failure.printStackTrace(System.err);
            }
        }

        System.out.println("SUMMARY " + passed + " passed, " + failures.size() + " failed");
        if (!failures.isEmpty()) {
            throw new AssertionError("Relational pipeline test failures: " + failures);
        }
    }

    private static void schemaAndRowBasics() {
        Column id = new Column("id", DataType.INT);
        Column name = new Column("name", DataType.TEXT);
        Schema schema = Schema.of(id, name);

        assertColumnOrder(schema, "id", "name");
        assertSame(id, schema.column(0), "Schema.column(0) must return the id column");
        assertSame(name, schema.column(1), "Schema.column(1) must return the name column");
        assertSame(schema.column(0), schema.columns().get(0),
                "Schema.column and Schema.columns must describe the same first column");

        Row row = Row.of(schema, 7, "seven");
        assertSame(schema, row.schema(), "Row must retain its immutable schema");
        assertEquals(Arrays.asList(7, "seven"), row.values(), "Row.values mismatch");
        assertEquals(7, row.value(0), "Row.value(int) mismatch");
        assertEquals("seven", row.value("name"), "Row.value(String) mismatch");
    }

    private static void scanPreservesStableOrdering() {
        Schema schema = peopleSchema();
        List<Row> input = Arrays.asList(
                Row.of(schema, 3, "c"),
                Row.of(schema, 1, "a"),
                Row.of(schema, 2, "b"),
                Row.of(schema, 1, "a-again"));
        ScanOperator scan = new ScanOperator(schema, input);

        assertColumnOrder(scan.outputSchema(), "id", "name");
        assertEquals(
                tuples(tuple(3, "c"), tuple(1, "a"), tuple(2, "b"), tuple(1, "a-again")),
                collectValues(scan),
                "Scan must return each row once in input order");
    }

    private static void filterHandlesNoneSomeAndAll() {
        Schema schema = peopleSchema();
        List<Row> input = Arrays.asList(
                Row.of(schema, 1, "first"),
                Row.of(schema, 2, "second-a"),
                Row.of(schema, 3, "third"),
                Row.of(schema, 2, "second-b"));

        Operator none = new FilterOperator(
                new ScanOperator(schema, input),
                new ColumnPredicate(schema, "id", ColumnPredicate.Comparison.LESS_THAN, 0));
        assertColumnOrder(none.outputSchema(), "id", "name");
        assertEquals(Collections.emptyList(), collectValues(none),
                "Filter that matches no rows returned data");

        Operator some = new FilterOperator(
                new ScanOperator(schema, input),
                new ColumnPredicate(schema, "id", ColumnPredicate.Comparison.EQUAL, 2));
        assertEquals(
                tuples(tuple(2, "second-a"), tuple(2, "second-b")),
                collectValues(some),
                "Filter must preserve the relative order of matching rows");

        Operator all = new FilterOperator(
                new ScanOperator(schema, input),
                new ColumnPredicate(schema, "id", ColumnPredicate.Comparison.GREATER_THAN, 0));
        assertEquals(
                tuples(
                        tuple(1, "first"),
                        tuple(2, "second-a"),
                        tuple(3, "third"),
                        tuple(2, "second-b")),
                collectValues(all),
                "Filter that matches all rows must preserve the complete input order");

        Operator textEquality = new FilterOperator(
                new ScanOperator(schema, input),
                new ColumnPredicate(
                        schema, "name", ColumnPredicate.Comparison.EQUAL, "third"));
        assertEquals(tuples(tuple(3, "third")), collectValues(textEquality),
                "TEXT equality filter mismatch");
    }

    private static void projectionReordersValuesAndSchema() {
        Schema schema = peopleSchema();
        List<Row> input = Arrays.asList(
                Row.of(schema, 10, "ten"),
                Row.of(schema, 20, "twenty"));
        ProjectOperator project = new ProjectOperator(
                new ScanOperator(schema, input), Arrays.asList("name", "id"));

        assertColumnOrder(project.outputSchema(), "name", "id");
        assertEquals(DataType.TEXT, project.outputSchema().column(0).type(),
                "Projected name column type mismatch");
        assertEquals(DataType.INT, project.outputSchema().column(1).type(),
                "Projected id column type mismatch");
        List<Row> output = collectRows(project);
        assertEquals(2, output.size(), "Projection row count mismatch");
        assertEquals(tuple("ten", 10), output.get(0).values(), "First projected row mismatch");
        assertEquals(tuple("twenty", 20), output.get(1).values(), "Second projected row mismatch");
        for (int i = 0; i < output.size(); i++) {
            assertColumnOrder(output.get(i).schema(), "name", "id");
            assertEquals(output.get(i).value("name"), output.get(i).value(0),
                    "Projected name lookup mismatch at output row " + i);
            assertEquals(output.get(i).value("id"), output.get(i).value(1),
                    "Projected id lookup mismatch at output row " + i);
        }
    }

    private static void limitBoundaryCases() {
        Schema schema = peopleSchema();
        List<Row> input = Arrays.asList(
                Row.of(schema, 1, "one"),
                Row.of(schema, 2, "two"),
                Row.of(schema, 3, "three"));

        assertEquals(Collections.emptyList(),
                collectValues(new LimitOperator(new ScanOperator(schema, input), 0)),
                "Limit zero must return no rows");
        assertEquals(tuples(tuple(1, "one")),
                collectValues(new LimitOperator(new ScanOperator(schema, input), 1)),
                "Limit one mismatch");
        assertEquals(tuples(tuple(1, "one"), tuple(2, "two"), tuple(3, "three")),
                collectValues(new LimitOperator(new ScanOperator(schema, input), 3)),
                "Limit equal to input size mismatch");
        LimitOperator greater = new LimitOperator(new ScanOperator(schema, input), 99);
        assertColumnOrder(greater.outputSchema(), "id", "name");
        assertEquals(tuples(tuple(1, "one"), tuple(2, "two"), tuple(3, "three")),
                collectValues(greater),
                "Limit greater than input size mismatch");
    }

    private static void fullComposedPipeline() {
        Schema schema = peopleSchema();
        List<Row> input = new ArrayList<>();
        for (int id = 1; id <= 7; id++) {
            input.add(Row.of(schema, id, "person-" + id));
        }

        Operator pipeline = new LimitOperator(
                new ProjectOperator(
                        new FilterOperator(
                                new FilterOperator(
                                        new ScanOperator(schema, input),
                                        new ColumnPredicate(
                                                schema,
                                                "id",
                                                ColumnPredicate.Comparison.GREATER_THAN,
                                                1)),
                                new ColumnPredicate(
                                        schema,
                                        "id",
                                        ColumnPredicate.Comparison.LESS_THAN,
                                        7)),
                        Arrays.asList("name", "id")),
                3);

        assertColumnOrder(pipeline.outputSchema(), "name", "id");
        assertEquals(
                tuples(tuple("person-2", 2), tuple("person-3", 3), tuple("person-4", 4)),
                collectValues(pipeline),
                "Limit(Project(Filter(Filter(Scan)))) result mismatch");
    }

    private static void validationFailuresAreTyped() {
        expectThrows(
                SchemaException.class,
                () -> Schema.of(
                        new Column("duplicate", DataType.INT),
                        new Column("duplicate", DataType.TEXT)),
                "Duplicate schema columns must be rejected");

        Schema schema = peopleSchema();
        assertEquals(-1, schema.indexOf("absent"),
                "Schema.indexOf must report a missing column with -1");

        expectThrows(
                RowValidationException.class,
                () -> new Row(schema, Collections.singletonList(1)),
                "A row with too few values must be rejected");
        expectThrows(
                RowValidationException.class,
                () -> Row.of(schema, "not-an-int", "name"),
                "A TEXT value in an INT column must be rejected");
        expectThrows(
                RowValidationException.class,
                () -> Row.of(schema, 1, 2),
                "An INT value in a TEXT column must be rejected");

        expectThrows(
                PredicateValidationException.class,
                () -> new ColumnPredicate(
                        schema, "id", ColumnPredicate.Comparison.EQUAL, "not-an-int"),
                "Predicate literal must match an INT column");
        expectThrows(
                PredicateValidationException.class,
                () -> new ColumnPredicate(
                        schema, "name", ColumnPredicate.Comparison.EQUAL, 42),
                "Predicate literal must match a TEXT column");
        expectThrows(
                PredicateValidationException.class,
                () -> new ColumnPredicate(
                        schema, "absent", ColumnPredicate.Comparison.EQUAL, "anything"),
                "Predicate column must exist");
        expectThrows(
                PredicateValidationException.class,
                () -> new ColumnPredicate(
                        schema, "name", ColumnPredicate.Comparison.LESS_THAN, "middle"),
                "Ordered comparisons on TEXT columns must be rejected");

        expectThrows(
                OperatorArgumentException.class,
                () -> new ProjectOperator(
                        new ScanOperator(schema, Collections.emptyList()),
                        Arrays.asList("id", "id")),
                "Duplicate projection columns must be rejected");
        expectThrows(
                OperatorArgumentException.class,
                () -> new ProjectOperator(
                        new ScanOperator(schema, Collections.emptyList()),
                        Collections.singletonList("absent")),
                "Missing projection columns must be rejected");
        expectThrows(
                OperatorArgumentException.class,
                () -> new ProjectOperator(
                        new ScanOperator(schema, Collections.emptyList()),
                        Collections.emptyList()),
                "Empty projection must be rejected");
        expectThrows(
                OperatorArgumentException.class,
                () -> new LimitOperator(
                        new ScanOperator(schema, Collections.emptyList()), -1),
                "Negative limits must be rejected");
    }

    private static void operatorLifecycleContract() {
        Schema schema = peopleSchema();
        List<Row> oneRow = Collections.singletonList(Row.of(schema, 1, "one"));

        assertStandardLifecycle("scan", new ScanOperator(schema, oneRow));
        assertStandardLifecycle(
                "filter",
                new FilterOperator(
                        new ScanOperator(schema, oneRow),
                        new ColumnPredicate(
                                schema, "id", ColumnPredicate.Comparison.EQUAL, 1)));
        assertStandardLifecycle(
                "project",
                new ProjectOperator(
                        new ScanOperator(schema, oneRow), Collections.singletonList("id")));
        assertStandardLifecycle(
                "limit", new LimitOperator(new ScanOperator(schema, oneRow), 1));

        ScanOperator empty = new ScanOperator(schema, Collections.emptyList());
        empty.open();
        for (int attempt = 1; attempt <= 3; attempt++) {
            PullResult result = empty.pull();
            assertTrue(result.isEndOfStream(),
                    "Empty scan pull " + attempt + " must repeatedly return end-of-stream");
        }
        empty.close();
        empty.close();

        ScanOperator closedBeforeOpen = new ScanOperator(schema, oneRow);
        expectThrows(
                LifecycleException.class,
                closedBeforeOpen::close,
                "Close-before-open must fail");
        closedBeforeOpen.open();
        closedBeforeOpen.close();
        closedBeforeOpen.close();
    }

    private static void earlyClosePropagatesExactlyOnce() {
        Schema schema = peopleSchema();
        List<Row> input = Arrays.asList(
                Row.of(schema, 1, "one"),
                Row.of(schema, 2, "two"),
                Row.of(schema, 3, "three"));
        CountingOperator source = new CountingOperator(new ScanOperator(schema, input));
        Operator pipeline = new LimitOperator(
                new ProjectOperator(
                        new FilterOperator(
                                source,
                                new ColumnPredicate(
                                        schema,
                                        "id",
                                        ColumnPredicate.Comparison.GREATER_THAN,
                                        0)),
                        Collections.singletonList("id")),
                100);

        pipeline.open();
        PullResult first = pipeline.pull();
        assertFalse(first.isEndOfStream(), "First pipeline pull unexpectedly reached EOS");
        assertEquals(1, first.row().value("id"), "First early-close row mismatch");
        pipeline.close();
        pipeline.close();

        assertEquals(1, source.openCalls, "Downstream open must propagate exactly once");
        assertEquals(1, source.pullCalls, "Early-close test should consume exactly one source row");
        assertEquals(1, source.closeCalls, "Repeated downstream close must propagate exactly once");

        CountingOperator limitedSource = new CountingOperator(new ScanOperator(schema, input));
        LimitOperator one = new LimitOperator(limitedSource, 1);
        one.open();
        assertFalse(one.pull().isEndOfStream(), "Limit one must return its first row");
        assertTrue(one.pull().isEndOfStream(), "Limit one must reach EOS after one row");
        assertTrue(one.pull().isEndOfStream(), "Limit EOS must be repeatable");
        one.close();
        one.close();
        assertEquals(1, limitedSource.pullCalls,
                "Limit must not over-pull its child after reaching its bound");
        assertEquals(1, limitedSource.closeCalls,
                "Repeated close after limit EOS must propagate exactly once");

        CountingOperator zeroSource = new CountingOperator(new ScanOperator(schema, input));
        LimitOperator zero = new LimitOperator(zeroSource, 0);
        zero.open();
        assertTrue(zero.pull().isEndOfStream(), "Limit zero must immediately reach EOS");
        assertTrue(zero.pull().isEndOfStream(), "Limit zero EOS must be repeatable");
        zero.close();
        assertEquals(0, zeroSource.pullCalls,
                "Limit zero must not pull a data row from its child");
        assertEquals(1, zeroSource.closeCalls,
                "Limit zero must still close its child exactly once");
    }

    private static void composedEndOfStreamIsStable() {
        Schema schema = peopleSchema();
        CountingOperator source = new CountingOperator(
                new ScanOperator(schema, Collections.singletonList(Row.of(schema, 1, "one"))));
        Operator pipeline = new ProjectOperator(
                new FilterOperator(
                        source,
                        new ColumnPredicate(
                                schema, "id", ColumnPredicate.Comparison.EQUAL, 1)),
                Collections.singletonList("id"));

        pipeline.open();
        assertFalse(pipeline.pull().isEndOfStream(),
                "Composed pipeline must emit its matching row");
        assertTrue(pipeline.pull().isEndOfStream(),
                "Composed pipeline must report natural EOS");
        int pullsAtEnd = source.pullCalls;
        assertTrue(pipeline.pull().isEndOfStream(),
                "Composed pipeline EOS must remain stable");
        assertEquals(pullsAtEnd, source.pullCalls,
                "A repeated root EOS pull must not consult the source again");
        pipeline.close();
        pipeline.close();
        assertEquals(1, source.closeCalls,
                "Natural exhaustion plus repeated root close must close the source once");
    }

    private static void failedOpenRollsBackOnce() {
        FailingOpenOperator operator = new FailingOpenOperator(peopleSchema());
        expectThrows(
                OperatorArgumentException.class,
                operator::open,
                "The original open failure must reach the caller");
        assertEquals(1, operator.openHookCalls,
                "A failed open must invoke its open hook once");
        assertEquals(1, operator.closeHookCalls,
                "A failed open must attempt rollback exactly once");
        operator.close();
        assertEquals(1, operator.closeHookCalls,
                "Close after failed-open rollback must not retry cleanup");
        expectThrows(
                LifecycleException.class,
                operator::open,
                "A failed open must leave the operator terminal");

        FailingChildOperator child = new FailingChildOperator(peopleSchema());
        LimitOperator parent = new LimitOperator(child, 1);
        expectThrows(
                OperatorArgumentException.class,
                parent::open,
                "A child's open failure must reach the root caller");
        assertEquals(1, child.openCalls,
                "A unary operator must attempt child open once");
        assertEquals(1, child.closeCalls,
                "A unary operator must attempt cleanup when a custom child open fails");
        parent.close();
        assertEquals(1, child.closeCalls,
                "Close after parent failed-open rollback must not retry child cleanup");

        FailingOpenAndCloseOperator twoFailures =
                new FailingOpenAndCloseOperator(peopleSchema());
        OperatorArgumentException primary = expectThrows(
                OperatorArgumentException.class,
                twoFailures::open,
                "An open failure must remain primary when rollback also fails");
        assertEquals(1, primary.getSuppressed().length,
                "A distinct rollback failure must be retained exactly once");
        assertTrue(primary.getSuppressed()[0] instanceof LifecycleException,
                "The suppressed failure must be the rollback failure");
        assertEquals(1, twoFailures.closeHookCalls,
                "A throwing rollback hook must still run only once");
        twoFailures.close();
        assertEquals(1, twoFailures.closeHookCalls,
                "Close must not retry a rollback that already failed");
    }

    private static void collectionOwnershipAndImmutability() {
        Column id = new Column("id", DataType.INT);
        Column name = new Column("name", DataType.TEXT);
        List<Column> suppliedColumns = new ArrayList<>(Arrays.asList(id, name));
        Schema schema = new Schema(suppliedColumns);
        suppliedColumns.clear();
        assertColumnOrder(schema, "id", "name");
        expectThrows(
                UnsupportedOperationException.class,
                () -> schema.columns().clear(),
                "Schema.columns must be immutable");

        List<Object> suppliedValues = new ArrayList<>(Arrays.asList(1, "original"));
        Row original = new Row(schema, suppliedValues);
        suppliedValues.set(0, 999);
        suppliedValues.set(1, "mutated");
        assertEquals(tuple(1, "original"), original.values(),
                "Row must defensively copy its supplied values");
        expectThrows(
                UnsupportedOperationException.class,
                () -> original.values().set(0, 100),
                "Row.values must be immutable");

        Row replacement = Row.of(schema, 2, "replacement");
        List<Row> suppliedRows = new ArrayList<>(Collections.singletonList(original));
        ScanOperator scan = new ScanOperator(schema, suppliedRows);
        suppliedRows.clear();
        suppliedRows.add(replacement);
        assertEquals(tuples(tuple(1, "original")), collectValues(scan),
                "Scan must own a defensive copy of its input row list");

        List<String> suppliedProjection = new ArrayList<>(Collections.singletonList("id"));
        ProjectOperator project = new ProjectOperator(
                new ScanOperator(schema, Collections.singletonList(original)), suppliedProjection);
        suppliedProjection.set(0, "name");
        expectThrows(
                UnsupportedOperationException.class,
                () -> project.columnNames().set(0, "name"),
                "Project.columnNames must be immutable");
        assertColumnOrder(project.outputSchema(), "id");
        assertEquals(tuples(tuple(1)), collectValues(project),
                "Project must own a defensive copy of its column-name list");
    }

    private static void fixedSeedDataAgreesWithIndependentOracle() {
        final long seed = 0x5EEDC0DEL;
        final int generatedCount = 240;
        final int resultLimit = 37;
        Random random = new Random(seed);
        List<GeneratedRecord> generated = new ArrayList<>();
        for (int id = 0; id < generatedCount; id++) {
            generated.add(new GeneratedRecord(id, "tag-" + random.nextInt(19),
                    random.nextInt(121) - 20));
        }

        // This expected result is deliberately computed from plain objects, without using any
        // relational classes, predicates, or operator output.
        List<List<Object>> oracle = new ArrayList<>();
        for (GeneratedRecord record : generated) {
            if (record.score > 15 && record.score < 70) {
                oracle.add(tuple(record.tag, record.id));
                if (oracle.size() == resultLimit) {
                    break;
                }
            }
        }

        Schema schema = Schema.of(
                new Column("id", DataType.INT),
                new Column("tag", DataType.TEXT),
                new Column("score", DataType.INT));
        List<Row> input = new ArrayList<>();
        for (GeneratedRecord record : generated) {
            input.add(Row.of(schema, record.id, record.tag, record.score));
        }
        Operator pipeline = new LimitOperator(
                new ProjectOperator(
                        new FilterOperator(
                                new FilterOperator(
                                        new ScanOperator(schema, input),
                                        new ColumnPredicate(
                                                schema,
                                                "score",
                                                ColumnPredicate.Comparison.GREATER_THAN,
                                                15)),
                                new ColumnPredicate(
                                        schema,
                                        "score",
                                        ColumnPredicate.Comparison.LESS_THAN,
                                        70)),
                        Arrays.asList("tag", "id")),
                resultLimit);

        List<List<Object>> actual = collectValues(pipeline);
        assertEquals(resultLimit, oracle.size(),
                "Fixed seed did not generate enough oracle rows for the intended limit test");
        assertEquals(oracle, actual,
                "Fixed-seed relational result differs from the independent list oracle");
    }

    private static void assertStandardLifecycle(String operatorName, Operator operator) {
        expectThrows(
                LifecycleException.class,
                operator::pull,
                operatorName + " pull-before-open must fail");
        operator.open();
        expectThrows(
                LifecycleException.class,
                operator::open,
                operatorName + " double-open must fail");
        operator.close();
        operator.close();
        expectThrows(
                LifecycleException.class,
                operator::pull,
                operatorName + " pull-after-close must fail");
    }

    private static List<Row> collectRows(Operator operator) {
        List<Row> output = new ArrayList<>();
        boolean opened = false;
        try {
            operator.open();
            opened = true;
            int pulls = 0;
            while (true) {
                pulls++;
                if (pulls > 100_000) {
                    throw new AssertionError(
                            "Operator failed to reach end-of-stream within 100000 pulls");
                }
                PullResult result = operator.pull();
                if (result.isEndOfStream()) {
                    return output;
                }
                Row row = result.row();
                if (row == null) {
                    throw new AssertionError("Non-EOS PullResult returned a null row");
                }
                output.add(row);
            }
        } finally {
            if (opened) {
                operator.close();
            }
        }
    }

    private static List<List<Object>> collectValues(Operator operator) {
        List<List<Object>> values = new ArrayList<>();
        for (Row row : collectRows(operator)) {
            values.add(new ArrayList<>(row.values()));
        }
        return values;
    }

    private static Schema peopleSchema() {
        return Schema.of(
                new Column("id", DataType.INT),
                new Column("name", DataType.TEXT));
    }

    private static void assertColumnOrder(Schema schema, String... expectedNames) {
        assertEquals(expectedNames.length, schema.size(),
                "Schema size mismatch for expected columns " + Arrays.toString(expectedNames));
        assertEquals(expectedNames.length, schema.columns().size(),
                "Schema.columns size disagrees with Schema.size");
        for (int index = 0; index < expectedNames.length; index++) {
            String name = expectedNames[index];
            assertEquals(index, schema.indexOf(name),
                    "Schema index mismatch for column " + name);
            assertNotNull(schema.column(index), "Schema.column(" + index + ") returned null");
            assertSame(schema.column(index), schema.columns().get(index),
                    "Schema accessors disagree at index " + index);
        }
    }

    private static List<Object> tuple(Object... values) {
        return Arrays.asList(values);
    }

    @SafeVarargs
    private static List<List<Object>> tuples(List<Object>... rows) {
        return Arrays.asList(rows);
    }

    private static void assertTrue(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message + " (expected true, actual false)");
        }
    }

    private static void assertFalse(boolean condition, String message) {
        if (condition) {
            throw new AssertionError(message + " (expected false, actual true)");
        }
    }

    private static void assertNotNull(Object actual, String message) {
        if (actual == null) {
            throw new AssertionError(message + " (expected non-null, actual null)");
        }
    }

    private static void assertSame(Object expected, Object actual, String message) {
        if (expected != actual) {
            throw new AssertionError(
                    message + " (expected same instance " + expected + ", actual " + actual + ")");
        }
    }

    private static void assertEquals(Object expected, Object actual, String message) {
        if (!Objects.equals(expected, actual)) {
            throw new AssertionError(
                    message + " (expected <" + expected + ">, actual <" + actual + ">)");
        }
    }

    private static <T extends Throwable> T expectThrows(
            Class<T> expectedType, ThrowingRunnable action, String message) {
        try {
            action.run();
        } catch (Throwable actual) {
            if (expectedType.isInstance(actual)) {
                return expectedType.cast(actual);
            }
            throw new AssertionError(
                    message + " (expected " + expectedType.getName() + ", caught "
                            + actual.getClass().getName() + ": " + actual.getMessage() + ")",
                    actual);
        }
        throw new AssertionError(
                message + " (expected " + expectedType.getName() + ", but nothing was thrown)");
    }

    private interface ThrowingRunnable {
        void run() throws Exception;
    }

    private static final class NamedTest {
        private final String name;
        private final ThrowingRunnable body;

        private NamedTest(String name, ThrowingRunnable body) {
            this.name = name;
            this.body = body;
        }
    }

    private static final class GeneratedRecord {
        private final int id;
        private final String tag;
        private final int score;

        private GeneratedRecord(int id, String tag, int score) {
            this.id = id;
            this.tag = tag;
            this.score = score;
        }
    }

    /** A deliberately small spy that leaves row production to a real operator. */
    private static final class CountingOperator implements Operator {
        private final Operator delegate;
        private int openCalls;
        private int pullCalls;
        private int closeCalls;

        private CountingOperator(Operator delegate) {
            this.delegate = delegate;
        }

        @Override
        public Schema outputSchema() {
            return delegate.outputSchema();
        }

        @Override
        public void open() {
            openCalls++;
            delegate.open();
        }

        @Override
        public PullResult pull() {
            pullCalls++;
            return delegate.pull();
        }

        @Override
        public void close() {
            closeCalls++;
            delegate.close();
        }
    }

    private static final class FailingOpenOperator extends AbstractOperator {
        private int openHookCalls;
        private int closeHookCalls;

        private FailingOpenOperator(Schema schema) {
            super(schema);
        }

        @Override
        protected void onOpen() {
            openHookCalls++;
            throw new OperatorArgumentException("deliberate open failure");
        }

        @Override
        protected PullResult onPull() {
            throw new AssertionError("failed-open operator must never be pulled");
        }

        @Override
        protected void onClose() {
            closeHookCalls++;
        }
    }

    private static final class FailingChildOperator implements Operator {
        private final Schema schema;
        private int openCalls;
        private int closeCalls;

        private FailingChildOperator(Schema schema) {
            this.schema = schema;
        }

        @Override
        public Schema outputSchema() {
            return schema;
        }

        @Override
        public void open() {
            openCalls++;
            throw new OperatorArgumentException("deliberate child open failure");
        }

        @Override
        public PullResult pull() {
            throw new AssertionError("failed child must never be pulled");
        }

        @Override
        public void close() {
            closeCalls++;
        }
    }

    private static final class FailingOpenAndCloseOperator extends AbstractOperator {
        private int closeHookCalls;

        private FailingOpenAndCloseOperator(Schema schema) {
            super(schema);
        }

        @Override
        protected void onOpen() {
            throw new OperatorArgumentException("primary open failure");
        }

        @Override
        protected PullResult onPull() {
            throw new AssertionError("failed-open operator must never be pulled");
        }

        @Override
        protected void onClose() {
            closeHookCalls++;
            throw new LifecycleException("suppressed rollback failure");
        }
    }
}
