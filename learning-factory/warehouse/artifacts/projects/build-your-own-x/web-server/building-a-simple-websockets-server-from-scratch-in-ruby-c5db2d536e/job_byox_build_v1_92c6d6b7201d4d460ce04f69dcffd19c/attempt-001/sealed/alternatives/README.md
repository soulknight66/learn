# Sealed alternatives

## Selector-driven reactor

Keep sockets nonblocking and register them with `IO.select` or a platform event
API. Each connection owns an input buffer, decoder, fragment state, and queued
output buffers. One reactor thread advances state only when a descriptor is
ready. This reduces thread cost for idle clients but makes fairness, partial
writes, callback isolation, and shutdown more complex. Slow callbacks must move
to a bounded executor, which introduces message ordering and backpressure
questions.

## Fixed worker pool

An acceptor can submit admitted sockets to a bounded queue consumed by a fixed
number of blocking workers. This bounds threads but one connection occupies a
worker for its entire lifetime, so a handful of idle clients can starve queued
connections. Assigning frames rather than connections to workers begins to
resemble a reactor and requires strict per-connection ordering.

## Front-end HTTP handoff

A mature HTTP server can perform routing, TLS, header limits, authentication,
and upgrade validation, then hand a hijacked stream to a WebSocket component.
This removes duplicated HTTP parsing but ties the implementation to the front
end's lifecycle and stream-hijack API. Care is still required to transfer any
bytes read past the HTTP boundary.

## Library-based deployment

For real services, a maintained WebSocket library is preferable. It provides
interoperability coverage, negotiated extensions, and ecosystem integration.
The from-scratch reference exists to expose protocol mechanics, not to justify
reimplementing security-sensitive networking in production.

