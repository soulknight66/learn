# Reference tradeoffs

- The router supports static, named, and final wildcard segments, not regular-expression routes,
  optional groups, subrouters, or host routing. A narrow grammar is easier to validate and reason
  about.
- Middleware is promise-oriented rather than fully compatible with callback-era Express handlers.
  This makes onion ordering and rejection propagation deterministic, at the cost of rejecting code
  that schedules `next()` later without returning it.
- Request bodies are buffered after a streaming size check. That is appropriate for small JSON but
  not large uploads or streaming transforms.
- The request-target uses WHATWG URL parsing. Duplicate query entries survive in `URLSearchParams`
  rather than being coerced into a plain object.
- Route layers are scanned linearly. This preserves registration order and is adequate for a
  learning framework; a trie can improve lookup for very large route tables but complicates ordered
  middleware semantics.
- `HEAD` follows the first registration-order layer eligible for HEAD, including GET fallback. An
  explicit HEAD route must be registered earlier than a GET route to override it.
- The default error boundary is deliberately small and has no logging hook. Avoiding accidental
  disclosure is valuable, but production operators would need structured observability.
- A request snapshots the layer list but response helpers remain mutable properties on the native
  response object. A symbol prevents duplicate decoration; it does not attempt namespace isolation
  from every possible user extension.
