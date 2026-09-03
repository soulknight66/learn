# Requirements

Implement the CommonJS package in `starter/` using only Node.js built-ins. All normative terms
(`MUST`, `MUST NOT`, and `SHOULD`) are intentional.

## R1 — Public API

- `require('./starter')` MUST return a `createApplication` function.
- Calling it MUST return a callable `(req, res)` request listener with methods `use`, `get`, `post`,
  `put`, `patch`, `delete`, `head`, `options`, and `listen`.
- The package MUST also export `createApplication`, `json`, and `HttpError` as properties.
- Registration methods MUST return the application for chaining.
- `listen(...args)` MUST create a fresh `node:http` server, call `server.listen(...args)`, and return
  that server.

## R2 — Middleware

- `app.use(handler)` registers global middleware.
- `app.use('/prefix', handler)` registers middleware whose prefix matches either exactly or at a
  slash boundary. `/api` MUST NOT match `/apricot`.
- Middleware receives `(req, res, next)`, executes in registration order, and can stop the chain by
  not calling `next`.
- Delegating middleware MUST return or await `next()`. Calling the same `next` callback more than
  once MUST become a server error rather than executing downstream work twice.
- A synchronous throw or rejected promise MUST reach the error translator.

## R3 — Routing

- A route pattern begins with `/` and consists of static segments, named segments such as `:id`,
  and at most one final wildcard such as `*rest`.
- Parameter names MUST match `[A-Za-z_][A-Za-z0-9_]*` and MUST be unique within a pattern.
- Static text is literal, matching is case-sensitive, and one trailing slash is accepted.
- Named segments match one non-empty encoded segment. A final wildcard matches the remaining path,
  including an empty remainder.
- Captures MUST be decoded with `decodeURIComponent`. Malformed escapes MUST produce status 400.
- Route layers and middleware MUST honor registration order. A route can delegate to later layers by
  calling `next`.
- `HEAD` may fall back to a matching `GET` layer. An explicit earlier `HEAD` layer takes precedence.
- If no layer matches the path, respond 404. If the path has routes but the method is unsupported,
  respond 405 and include a deterministic `Allow` header. `OPTIONS` on a known path responds 204
  with the same `Allow` set.
- If a route for the request method matches but the chain finishes without a response, the terminal
  response MUST be 404. The mere existence of an `Allow` set MUST NOT turn a supported method into
  405. This rule also applies to `HEAD` through explicit routing or `GET` fallback.

## R4 — Request state

For every request, before user middleware runs:

- `req.originalUrl` is the original request-target string.
- `req.path` is the pathname parsed against a fixed local base URL; routing MUST NOT trust `Host`.
- `req.query` is a `URLSearchParams` preserving duplicate keys.
- `req.params` is a new null-prototype object, never shared between requests.
- A matching route sets `req.routePattern` and route parameters only for that route's execution.

Concurrent requests MUST NOT leak bodies, parameters, status, headers, or application-temporary
state into one another.

## R5 — Response helpers

- `res.status(code)` validates an integer from 100 through 999, assigns `statusCode`, and returns
  `res`.
- `res.set(name, value)` sets a header and returns `res`.
- `res.send(value)` handles strings, Buffers, `null`/`undefined`, primitives, and objects. Plain
  objects and arrays delegate to JSON.
- `res.json(value)` serializes once and uses `application/json; charset=utf-8` unless already set.
- Text defaults to `text/plain; charset=utf-8`; Buffer data defaults to
  `application/octet-stream`.
- Helpers MUST set byte-accurate `Content-Length` when legal. Responses to `HEAD`, informational
  statuses, 204, and 304 MUST send no payload bytes. Statuses that forbid bodies MUST remove entity
  headers.
- A second helper call after the response ends MUST fail without writing another response.

## R6 — JSON body middleware

`json({ limit })` returns middleware:

- `limit` MUST be a positive safe integer and defaults to 1 MiB.
- It parses `application/json` and any media type ending in `+json`, ignoring media-type parameters.
- Nonmatching content types are not consumed and delegate unchanged.
- A non-identity `Content-Encoding` produces 415.
- A declared or observed body beyond the limit produces 413. A malformed `Content-Length`, stream
  error, or aborted request produces 400.
- Parser entry after an abort, destruction before readable end, or stream error has already occurred MUST
  still settle with 400; it MUST NOT wait for an event that has already fired.
- Empty JSON input becomes `null`; valid JSON can be any JSON value; malformed JSON produces 400.
- Each request body is buffered independently as bytes, then decoded as UTF-8 exactly once.

## R7 — Errors and lifecycle

- Operational errors use `HttpError(status, message, options)`.
- Before headers are sent, error responses are JSON with `{ "error": { "status", "message" } }`.
  Messages for unexpected 5xx failures MUST be replaced by `Internal Server Error`.
- An error's safe headers MAY be copied to the response. After headers are sent, the connection MUST
  be terminated instead of attempting a second response.
- Request listeners MUST observe returned promises so rejected work cannot become an unhandled
  rejection.

## R8 — Scope and quality

- No third-party runtime or test dependencies.
- No shell invocation, dynamic evaluation, busy waiting, or process-global request storage.
- Tests MUST bind an ephemeral loopback port and close it deterministically.
- Concurrency tests that claim overlap MUST use an explicit gate or latch rather than timing luck.
- Public tests are examples, not the complete specification.
