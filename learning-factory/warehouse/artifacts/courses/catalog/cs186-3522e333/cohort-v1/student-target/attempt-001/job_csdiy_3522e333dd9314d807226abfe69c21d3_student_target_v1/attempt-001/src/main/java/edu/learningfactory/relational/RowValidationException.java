package edu.learningfactory.relational;

/** Signals that a row does not conform to its required schema. */
public class RowValidationException extends RuntimeException {
    public RowValidationException(String message) {
        super(message);
    }

    public RowValidationException(String message, Throwable cause) {
        super(message, cause);
    }
}
