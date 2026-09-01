package dev.learningfactory.sprig;

import java.util.Objects;

/** A stable, source-located compiler diagnostic. */
public record Diagnostic(String code, int line, int column, String message)
        implements Comparable<Diagnostic> {
    public Diagnostic {
        code = Objects.requireNonNull(code, "code");
        message = Objects.requireNonNull(message, "message");
        if (code.isBlank()) {
            throw new IllegalArgumentException("code must not be blank");
        }
        if (line < 1 || column < 1) {
            throw new IllegalArgumentException("positions are one-based");
        }
    }

    @Override
    public int compareTo(Diagnostic other) {
        int byLine = Integer.compare(line, other.line);
        if (byLine != 0) return byLine;
        int byColumn = Integer.compare(column, other.column);
        if (byColumn != 0) return byColumn;
        return code.compareTo(other.code);
    }
}

