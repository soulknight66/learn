package org.learningfactory.mica;

import java.util.Objects;

public final class MicaException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    public enum Kind { LEX, PARSE, RUNTIME, LIMIT }

    private final Kind kind;
    private final int line;
    private final int column;
    private final String detail;

    public MicaException(Kind kind, int line, int column, String detail) {
        super("[" + Objects.requireNonNull(kind, "kind") + " " + line + ":" + column + "] "
                + Objects.requireNonNull(detail, "detail"));
        if (line < 1 || column < 1) {
            throw new IllegalArgumentException("error locations are one-based");
        }
        this.kind = kind;
        this.line = line;
        this.column = column;
        this.detail = detail;
    }

    public Kind kind() { return kind; }
    public int line() { return line; }
    public int column() { return column; }
    public String detail() { return detail; }
}
