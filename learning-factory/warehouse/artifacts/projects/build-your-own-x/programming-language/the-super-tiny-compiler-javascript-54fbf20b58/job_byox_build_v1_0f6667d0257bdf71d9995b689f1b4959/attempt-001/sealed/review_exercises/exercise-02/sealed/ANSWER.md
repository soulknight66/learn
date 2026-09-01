# Exercise 02 answer: environment membership

The `in` operator walks the prototype chain. Names such as `toString` and
`constructor` therefore appear declared before Pebble executes a declaration.
A read can expose a host function or constructor, a declaration can be rejected
as a false duplicate, and an assignment can alter an inherited-name shadow
rather than enforcing the language's declaration rule. The special
`__proto__` key also has legacy setter behavior on ordinary objects.

Use `Map` and its `has`, `get`, and `set` operations. A null-prototype object is
also viable if every membership test uses
`Object.prototype.hasOwnProperty.call(values, name)`, but `Map` states the
key/value-table intent more clearly and avoids special property syntax.

If nested lexical scopes are added, lookup should walk explicit `Environment`
parent links, not JavaScript prototypes. Tests should declare, read, and assign
prototype-shaped identifiers; reject assignment of a truly undeclared name;
reject a real duplicate; and require identical tree/VM observations. Treat a
host value crossing into Pebble as a boundary violation even if the current
language has no call operator with which to invoke it.
