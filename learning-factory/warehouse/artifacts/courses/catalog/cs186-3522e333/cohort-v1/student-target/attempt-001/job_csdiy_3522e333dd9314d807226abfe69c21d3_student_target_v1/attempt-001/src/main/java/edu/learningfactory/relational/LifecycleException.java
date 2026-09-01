package edu.learningfactory.relational;

/** Signals an invalid operator lifecycle operation. */
public class LifecycleException extends RuntimeException {
    public LifecycleException(String message) {
        super(message);
    }

    public LifecycleException(String message, Throwable cause) {
        super(message, cause);
    }
}
