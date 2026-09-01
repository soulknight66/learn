# Reference contract review

## Scope and evidence boundary

This review assesses the educational reference contract: a CommonJS
`createApplication` factory, ordered middleware and routes, error dispatch, and
small response helpers on top of Node's HTTP interfaces. It is a generated
review aid. It is not independent validation, does not confer a `REVIEWED`
label, and does not claim that the implementation was executed on a host where
Node.js is unavailable.

**No production-readiness claim is made for this reference implementation.**
It is intentionally a compact teaching target.

## Contract strengths

- Application state is created per factory call rather than hidden in a module
  singleton.
- Middleware order is explicit, mount matching respects path-segment
  boundaries, and routes have a deliberately small grammar.
- Request-derived maps are fresh plain objects. Special input names are added
  as own data properties, retaining the required public shape without invoking
  inherited setters, and the objects are never shared across requests.
- Path capture decoding has a deterministic malformed-input outcome.
- Synchronous throws, `next(error)`, and rejected handler Promises share one
  error channel, while each handler invocation may advance only once.
- HEAD routing is deliberately separate from GET; explicit HEAD and `all`
  routes may match, and every body-producing path suppresses wire body bytes.
- Default 404 and 500 responses are fixed and small, avoiding accidental
  exposure of exception messages. Malformed capture decoding enters ordinary
  error dispatch and therefore reaches the 500 default if it remains unhandled.

## Review risks and limitations

The surface is narrower than Express and should stay described that way.
Literal segments, `:name`, and a whole final `*` are the route grammar; regular
expressions, optional segments, nested routers, settings, templates, static
files, and body parsers are not implied. Changing that grammar would require
new ambiguity, decoding, and denial-of-service analysis.

The dispatcher is a linear educational design. Very large layer stacks and
large query strings can consume proportionally more CPU and allocation. Node's
HTTP parser supplies some wire-level constraints, but the framework does not
define application body limits, request deadlines, concurrency admission, or
per-client quotas.

Response helpers are convenience methods for bounded values, not a streaming
abstraction. Production work would need explicit backpressure, abort handling,
stream error ownership, conditional responses, compression policy, and a clear
rule for serialization failures after headers are committed.

The framework deliberately avoids exposing stack traces in its default 500.
That is a safe client default but insufficient operationally: real deployment
needs structured internal error reporting with credential and personal-data
redaction.

## Evidence still required

An independent validator should run, at minimum:

1. public and sealed reference tests on every supported Node version;
2. malformed target, duplicate query, mount-boundary, and wildcard cases;
3. overlapping async requests and repeated/late `next` calls;
4. GET/HEAD parity for status and representation headers;
5. socket abort and server lifecycle checks; and
6. package/structure scans proving learner-visible files contain no sealed
   answers.

The adversarial harness expands several of these checks, but a harness passing
its own generated reference is not independent evidence.
