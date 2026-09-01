package edu.learningfactory.relational;

/**
 * A pull-based relational operator.
 *
 * <p>A composite operator exclusively owns each child passed to it: clients open, pull, and close
 * only the root. Ownership starts when the root is successfully opened, and closing the root closes
 * every opened child at most once.</p>
 */
public interface Operator extends AutoCloseable {
    Schema outputSchema();

    void open();

    PullResult pull();

    @Override
    void close();
}
