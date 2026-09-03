# Reference design

## Application shape

`createApplication` owns an `Application` instance but returns a callable wrapper around `handle`,
decorated with bound registration and listening methods. The wrapper attaches a final rejection
observer, keeping the object usable by `node:http` while giving every chainable method one stable
public return value.

The application stores one immutable layer descriptor per registration. Middleware and routes share
that array, so interleaving `use` and route calls has visible, deterministic order. A request takes a
shallow snapshot before dispatch; registrations made while it is in flight apply only to later
requests.

## Continuations

`compose` copies its input stack and creates `furthestIndex` inside each invocation. Each `next`
dispatch must advance beyond that index. A repeated continuation therefore rejects rather than
running downstream code twice. Route handlers are composed as a nested stack whose terminal is the
outer layer's `next`, preserving the same invariant at both levels.

This is an awaitable middleware contract. A delegating handler must return or await `next()`;
callback-style delayed invocation without returning its promise is outside the contract.

## Path and method selection

Patterns compile at registration into anchored regular expressions. Captures are decoded only when
a route's method and expression both match. Before dispatch, `decodeURI` validates the pathname's
escape sequences without turning encoded slashes into separators.

The terminal handler tests compiled expressions without mutating the request and collects allowed
methods. It adds `HEAD` for `GET`, adds automatic `OPTIONS`, then sorts against a fixed method order.
It emits 405 only when the current method is absent from that set. A supported route chain that
finishes without a response therefore reaches the defined 404 fallback rather than being
misclassified as an unsupported method.

Route execution temporarily installs a new null-prototype parameter object and the registered
pattern. A `finally` block restores the previous values, which matters when one matching route
delegates to another.

## Requests and responses

The request-target is parsed against `http://local.invalid`; the `Host` header is never used for
routing. Each dispatch creates its own `URLSearchParams` and parameter object.

One internal `finish` function owns content type defaults, byte length, body-forbidden statuses, and
HEAD suppression. JSON serialization happens before that function and exactly once. A symbol marks
decoration without relying on names user code might already have.

## Body parsing

The JSON middleware filters media type before attaching stream listeners. It parses
`Content-Encoding` as a comma-separated token list, rejects malformed members with 400, and rejects
any non-identity coding with 415. It rejects over-limit declared lengths early, then counts Buffer
bytes as chunks arrive.
Before attachment it checks recorded error, abort, and pre-end close/destruction state. Abort, error,
close, end, and data listeners are then installed, followed by a second terminal-state check to
close the event-race window. Every settlement path removes its own listeners. On an observed limit
violation, it resumes the stream only to drain remaining input.

After buffering, an explicit fatal UTF-8 decoder rejects malformed byte sequences. Declared and
observed lengths must agree, an empty body becomes `null`, and JSON parsing occurs once.

## Error boundary

The application awaits the complete composed chain inside one `try` block. Before headers, failures
become a small JSON envelope; unexpected 5xx messages are hidden. Existing framing and
representation-encoding headers are cleared first, and only `Allow`, `Proxy-Authenticate`,
`Retry-After`, and `WWW-Authenticate` error metadata can be copied. Once headers have been sent, the
response socket is destroyed because a second status line or JSON envelope would corrupt the
protocol.
