# Adversarial harness expectations

These expectations explain the contract decisions encoded in
`adversarial/run.js`. They are instructor material, not additional public API.

1. Global middleware runs before matching mounted middleware, and a route runs
   afterward. The raw pathname stays percent-encoded in `req.path`, while
   captures are decoded. Duplicate query keys become arrays. Query and params
   containers are fresh plain objects; special names such as `__proto__`,
   `constructor`, and `toString` are installed as own data properties without
   changing the object's prototype.
2. A `/api` mount matches `/api` and `/api/...`, but not `/apiary`.
3. Only a final `*` is a wildcard. Its decoded remainder is stored under the
   numeric key `0` in `req.params`.
4. GET and HEAD are separate routes. A HEAD request selects an explicit HEAD or
   `all` route, never GET, and sends no response-body bytes.
5. `next(error)`, a synchronous throw, and a rejected handler Promise all enter
   the same error-middleware flow.
6. Every non-null, non-undefined `next` argument enters error mode, including
   `false`, `0`, and the empty string.
7. Only the first `next` call made by one handler invocation has an effect.
8. A malformed percent escape in a captured path becomes a `URIError` in error
   middleware; it does not terminate or corrupt the server.
9. Overlapping async requests have independent plain `req.params` objects.
10. Exhausting the stack in normal mode produces status 404 and `Not Found`;
    exhausting it in error mode produces status 500 and `Internal Server
    Error`. HEAD preserves their representation headers but emits no bytes.

A failed check identifies a contract mismatch; it does not by itself diagnose
the responsible function. The harness deliberately makes requests through
Node's HTTP server so response-helper and listener behavior are exercised
together.
