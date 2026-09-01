# Architectural alternatives

These alternatives are design comparisons, not additional implemented
solutions.

## Compiled segment matcher

The reference can compile each route into literal, parameter, and wildcard
segments at registration, then scan compiled layers in order. This keeps the
grammar auditable and registration errors early. Its lookup cost remains linear
in the number of layers, which is appropriate for a small teaching framework.

## Method-aware radix tree

A radix or segment trie can share literal prefixes and reduce lookup work for a
large route table. It makes registration order, parameter-vs-literal priority,
wildcards, HEAD fallback, and middleware interleaving substantially harder to
reason about. It is attractive only after profiling demonstrates route lookup
is material and a precise precedence contract exists.

## Precompiled regular expressions

Regex compilation gives a compact implementation for a richer path language.
It also creates escaping and capture-index complexity, and arbitrary patterns
can introduce pathological matching behavior. If adopted, accept only a
framework-owned grammar and compile it at registration; do not evaluate raw
request-controlled expressions.

## Composed middleware functions

Registration can build a composed function chain rather than walking layer
records for every request. Composition may reduce dispatch bookkeeping and can
make Promise flow natural. Dynamic route selection and error-mode transitions
still require careful ownership of `next`, and rebuilding compositions after
registration has lifecycle implications.

## Fetch-style request and response values

An alternative API could accept Web `Request` objects and return `Response`
objects. Immutable response values make double-send bugs less likely and ease
testing across runtimes. Adapting Node streams, abort signals, header timing,
and backpressure adds a translation layer and teaches a different model than
Node's `IncomingMessage`/`ServerResponse` pair.

## Adopt a maintained framework

For an actual service, using a maintained framework is usually preferable to
expanding this educational implementation. Mature projects bring ecosystem
integration, security processes, release discipline, and operational behavior
that cannot be reproduced by adding a few helpers. Selection should still be
based on measured requirements, maintenance health, and a threat model.
