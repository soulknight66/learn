package edu.learningfactory.minilog;

import java.io.IOException;

/** Signals complete but invalid durable bytes that recovery must not discard. */
public final class CorruptLogException extends IOException {
    public CorruptLogException(String message) {
        super(message);
    }

    public CorruptLogException(String message, Throwable cause) {
        super(message, cause);
    }
}
