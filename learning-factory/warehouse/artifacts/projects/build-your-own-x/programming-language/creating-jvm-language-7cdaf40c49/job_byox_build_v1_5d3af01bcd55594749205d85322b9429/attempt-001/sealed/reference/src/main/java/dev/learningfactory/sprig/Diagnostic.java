package dev.learningfactory.sprig;

import java.util.Objects;

public record Diagnostic(String code, int line, int column, String message)
        implements Comparable<Diagnostic> {
    public Diagnostic {
        code = Objects.requireNonNull(code, "code");
        message = Objects.requireNonNull(message, "message");
        if (code.isBlank()) throw new IllegalArgumentException("blank diagnostic code");
        if (line < 1 || column < 1) {
            throw new IllegalArgumentException("positions are one-based");
        }
    }

    @Override
    public int compareTo(Diagnostic other) {
        int result = Integer.compare(line, other.line);
        if (result == 0) result = Integer.compare(column, other.column);
        if (result == 0) result = code.compareTo(other.code);
        return result;
    }
}

