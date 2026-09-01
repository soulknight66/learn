# Reference review

## Correctness review

The implementation separates response framing from UTF-8 decoding, rejects conflicting length signals, accounts for DOM nodes and depth independently, and uses checked arithmetic for response and rendering sizes. The cascade correctly compares specificity before source order. Paint order is parent before child with canvas clipping.

The most important residual correctness gap is standards scope: vertical-only element layout does not implement a real inline formatting context. Whitespace collapsing and scalar-count wrapping are project-specific behavior, not HTML/CSS standards behavior.

## Security review

The core does not execute script, fetch subresources, follow redirects, decompress content, or open sockets. This meaningfully reduces attack surface. Parser budgets cover major memory/recursion dimensions, but CPU budgets and URL-length limits would still be needed around an exposed service.

`Transport` is a trust boundary. A future implementation must not resolve a hostname, approve it, and then reconnect by hostname; it should connect to an already approved resolved address. Every redirect requires the same policy again. HTTPS certificate validation cannot be safely improvised with the standard library.

## Readiness verdict

Educational reference only. It is not productionized, has not been compiled on the generation host, and needs independent tests plus fuzzing before even limited use with hostile input.
