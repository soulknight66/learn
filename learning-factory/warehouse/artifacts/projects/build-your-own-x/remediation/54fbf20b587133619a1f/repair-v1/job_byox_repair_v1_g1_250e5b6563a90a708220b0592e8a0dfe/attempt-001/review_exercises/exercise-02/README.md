# Exercise 02: environment membership

A proposed environment implementation replaces `Map` with a plain object:

```js
class Environment {
  constructor() {
    this.values = {};
  }

  declare(name, value) {
    if (name in this.values) {
      throw new PebbleRuntimeError(`Duplicate ${name}`, { code: "DUPLICATE_VARIABLE" });
    }
    this.values[name] = value;
  }

  assign(name, value) {
    if (!(name in this.values)) {
      throw new PebbleRuntimeError(`Unknown ${name}`, { code: "UNDEFINED_VARIABLE" });
    }
    this.values[name] = value;
  }

  read(name) {
    if (!(name in this.values)) {
      throw new PebbleRuntimeError(`Unknown ${name}`, { code: "UNDEFINED_VARIABLE" });
    }
    return this.values[name];
  }
}
```

Review questions:

1. Is membership restricted to names declared by the Pebble program?
2. Are all syntactically valid identifiers safe as object keys?
3. Can a read return a host-language value that Pebble never declared?
4. What representation or membership check makes the intended invariant
   explicit?
5. Which regression tests should run through both execution backends?

Treat this as a semantic boundary even when Pebble is only used locally.
