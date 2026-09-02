# Sealed design alternatives

These alternatives were considered but are not the reference contract.

## One router middleware

All routes could live in a separate router whose single dispatcher is mounted into the middleware
stack. Lookup becomes easier to optimize, but `use`, route, `use`, route registration order is no
longer naturally represented. Extra sequence numbers or multiple router mounts would be required.

## Trie routing

A segment trie reduces candidate patterns for large tables. Named and wildcard edges need defined
priority, while registration-order fallthrough still needs an ordered candidate list. The reference
uses a linear compiled-regex scan because semantics are clearer at challenge scale.

## Callback-compatible middleware

A dispatcher could keep a request pending until `res.finish`, `res.close`, or a callback fires,
allowing handlers that invoke `next` from an unreturned timer. That needs timeout and lifecycle
rules to distinguish delayed delegation from an intentional asynchronous response. The reference
instead adopts an explicit promise contract.

## Streaming JSON tokens

A tokenizer can avoid buffering a complete document, but building arbitrary JavaScript values still
requires memory proportional to the result and makes syntax/error positions much more complex. The
reference buffers only after enforcing a small byte limit.

## Raw TCP HTTP parsing

Implementing directly on `node:net` would expose framing, pipelining, and parser security in depth.
It is a different and substantially larger exercise. This project uses `node:http` and focuses on
framework dispatch above Node's HTTP parser.
