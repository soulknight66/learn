# Review 01 answer

## High-priority findings

1. **Mount matching ignores segment boundaries.** `startsWith("/api")` also
   accepts `/apiary`. A mount matches when the pathname equals the prefix, or
   when it starts with `prefix + "/"` (with a separate root-prefix rule).
2. **Untrusted encoding escapes the dispatch boundary.** `decodeURIComponent`
   throws `URIError` for `%ZZ`; nothing sends it through framework error
   dispatch. Decode captures in a guarded matching step and pass decoding
   failures to the same error path as a handler throw. With no error handler,
   the framework's deterministic non-leaking default is 500.
3. **Params belong to the router instead of the request.** Both overlapping
   handlers reference `sharedParams`. The second match overwrites `id`, so the
   first request eventually emits `second`. Create a fresh plain params object
   for every matching attempt and assign that object only to its request.
4. **A naive normal-object assignment gives special parameter names inherited
   meaning.** Although this sample uses only `id`, a generalized matcher can
   accept names such as `__proto__` or `constructor`. Preserve the required
   plain-object prototype while defining such accepted names as own data
   properties rather than invoking inherited setters.

Matching owns segment comparison and guarded decoding. Request initialization
owns fresh plain `query` and `params` objects. Dispatch owns propagation of
decoding and handler failures into error middleware, then the non-leaking 500
default if unhandled. Keeping those responsibilities separate also makes each
behavior independently testable.

The characterization intentionally reports mountHits `1`, concurrent bodies
`["second", "second"]`, and malformed result `URIError` for the flawed code.
