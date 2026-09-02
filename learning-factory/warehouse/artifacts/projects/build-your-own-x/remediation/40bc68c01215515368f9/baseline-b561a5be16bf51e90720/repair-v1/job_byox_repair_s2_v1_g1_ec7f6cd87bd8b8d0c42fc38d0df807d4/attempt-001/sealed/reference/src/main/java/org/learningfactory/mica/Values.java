package org.learningfactory.mica;

final class Values {
    private Values() { }

    static String render(Object value) {
        if (value == null) return "nil";
        if (value instanceof Boolean booleanValue) return booleanValue ? "true" : "false";
        if (value instanceof String stringValue) return stringValue;
        if (value instanceof Double number) {
            String text = Double.toString(number);
            if (Double.isFinite(number) && number == Math.rint(number)) {
                if (text.endsWith(".0")) return text.substring(0, text.length() - 2);
                int scientific = text.indexOf(".0E");
                if (scientific >= 0) return text.substring(0, scientific) + text.substring(scientific + 2);
            }
            return text;
        }
        throw new IllegalArgumentException("not a Mica value: " + value.getClass().getName());
    }

    static boolean equal(Object left, Object right) {
        if (left == null || right == null) return left == right;
        if (left instanceof Double a && right instanceof Double b) return a.doubleValue() == b.doubleValue();
        if (left instanceof String a && right instanceof String b) return a.equals(b);
        if (left instanceof Boolean a && right instanceof Boolean b) return a.equals(b);
        return false;
    }

    static double number(Object value, Token token, String context) {
        if (value instanceof Double number) return number;
        throw runtime(token, context + " requires a number, got " + typeName(value));
    }

    static boolean bool(Object value, Token token, String context) {
        if (value instanceof Boolean booleanValue) return booleanValue;
        throw runtime(token, context + " requires a boolean, got " + typeName(value));
    }

    static String typeName(Object value) {
        if (value == null) return "nil";
        if (value instanceof Double) return "number";
        if (value instanceof String) return "string";
        if (value instanceof Boolean) return "boolean";
        return "host value";
    }

    static MicaException runtime(Token token, String detail) {
        return new MicaException(MicaException.Kind.RUNTIME, token.line(), token.column(), detail);
    }
}
