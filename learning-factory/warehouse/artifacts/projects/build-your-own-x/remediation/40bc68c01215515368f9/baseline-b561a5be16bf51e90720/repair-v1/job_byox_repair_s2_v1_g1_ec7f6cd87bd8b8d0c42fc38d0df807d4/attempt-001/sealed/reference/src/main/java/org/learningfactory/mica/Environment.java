package org.learningfactory.mica;

import java.util.LinkedHashMap;
import java.util.Map;

final class Environment {
    private final Environment parent;
    private final Map<String, Object> values = new LinkedHashMap<>();

    Environment(Environment parent) {
        this.parent = parent;
    }

    void define(Token name, Object value) {
        if (values.containsKey(name.lexeme())) {
            throw Values.runtime(name, "variable '" + name.lexeme() + "' is already defined in this scope");
        }
        values.put(name.lexeme(), value);
    }

    Object get(Token name) {
        if (values.containsKey(name.lexeme())) return values.get(name.lexeme());
        if (parent != null) return parent.get(name);
        throw Values.runtime(name, "undefined variable '" + name.lexeme() + "'");
    }

    void assign(Token name, Object value) {
        if (values.containsKey(name.lexeme())) {
            values.put(name.lexeme(), value);
            return;
        }
        if (parent != null) {
            parent.assign(name, value);
            return;
        }
        throw Values.runtime(name, "undefined variable '" + name.lexeme() + "'");
    }
}
