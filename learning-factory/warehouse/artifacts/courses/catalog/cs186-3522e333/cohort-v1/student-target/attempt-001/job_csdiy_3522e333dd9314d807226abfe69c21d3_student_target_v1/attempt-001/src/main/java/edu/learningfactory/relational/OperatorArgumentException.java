package edu.learningfactory.relational;

/** Signals an invalid operator construction argument. */
public class OperatorArgumentException extends RuntimeException {
    public OperatorArgumentException(String message) {
        super(message);
    }

    public OperatorArgumentException(String message, Throwable cause) {
        super(message, cause);
    }
}
