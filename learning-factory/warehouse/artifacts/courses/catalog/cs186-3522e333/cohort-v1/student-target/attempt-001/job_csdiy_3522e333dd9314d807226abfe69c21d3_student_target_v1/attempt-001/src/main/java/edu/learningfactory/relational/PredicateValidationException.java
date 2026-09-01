package edu.learningfactory.relational;

/** Signals an invalid predicate definition. */
public class PredicateValidationException extends RuntimeException {
    public PredicateValidationException(String message) {
        super(message);
    }

    public PredicateValidationException(String message, Throwable cause) {
        super(message, cause);
    }
}
