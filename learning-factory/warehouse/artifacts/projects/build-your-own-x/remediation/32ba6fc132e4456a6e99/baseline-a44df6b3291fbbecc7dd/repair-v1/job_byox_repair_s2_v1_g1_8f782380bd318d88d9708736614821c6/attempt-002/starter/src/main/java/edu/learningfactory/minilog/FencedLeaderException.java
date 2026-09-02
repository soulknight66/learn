package edu.learningfactory.minilog;

/** An operation carried a term other than the active leader term. */
public final class FencedLeaderException extends IllegalStateException {
    public FencedLeaderException(String message) {
        super(message);
    }
}
