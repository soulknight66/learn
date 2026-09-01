# Concepts Behind the Challenge

This challenge combines a few small ideas whose interactions are more important
than any individual helper method.

## A function can also be an API object

Node's `http.createServer` expects a listener function. JavaScript functions are
objects, so the same function can own methods such as `use` and `listen`. Each
application needs its own registration stack captured by that function's
closure. This gives callers the convenient `http.createServer(app)` shape without
introducing shared global state.

## Registration is data; dispatch is request-local state

The route and middleware stack is application configuration. It persists across
requests and should be treated as read-only during dispatch. In contrast, the
current stack position, current handler position, error mode, params, and query
object belong to exactly one request.

Keeping those categories separate is the key to surviving concurrent requests.
An asynchronous handler can pause while another request runs through the same
application stack; neither request may overwrite the other's cursor or captures.

## Middleware is an ordered continuation chain

`next` is a continuation: calling it transfers control to the next eligible
handler. Eligibility depends on both path/method matching and whether dispatch is
currently carrying an error.

Error mode cannot be inferred from whether the carried value is truthy or even
non-null: JavaScript permits `throw undefined` and `Promise.reject(null)`. Those
operations still enter error mode and preserve their exact reasons, while an
explicit `next()`, `next(null)`, or `next(undefined)` continues in normal mode.

A robust dispatcher accounts for four ways a handler can behave:

- end the response;
- call `next()`;
- call `next(err)` or throw;
- return a promise that later fulfills or rejects.

The once-only rule matters because a buggy handler can call `next` twice, or call
`next` and later reject. Letting a stale continuation advance the stack again can
produce duplicate handlers, write-after-end failures, and state from one phase
appearing in another.

## Middleware prefixes are not string prefixes

The string `/api` is a prefix of `/apix`, but it is not a path-segment prefix.
Middleware mount matching therefore needs to examine the character immediately
after the prefix. Root middleware is the useful special case that matches every
pathname.

Routes use a different rule: the complete pathname must fit a small pattern.
Separating middleware matching from route matching makes both rules easier to
reason about and test.

## Compile configuration, capture values per request

Route patterns contain literals, named one-segment captures, and an optional
final wildcard. It is reasonable to validate and prepare a pattern when the route
is registered. Captured values must still be created anew on every match; a
compiled matcher must not store its latest params on itself.

Each matched middleware similarly starts with a fresh empty params object. Use
own-property checks and data-property creation when materializing query keys or
captures: names such as `__proto__` are input data, not invitations to invoke an
inherited setter.

Be deliberate about escaping literal text if the implementation uses regular
expressions. Route literals are data, not regex source.

## The URL has multiple useful views

The original request target is useful for logging and must remain unchanged. A
pathname is useful for matching. Decoded query values and route captures are
useful to application code. These views should be derived once per request, but
they should not be confused:

- query text never affects route matching;
- percent-decoding captures must not alter `originalUrl`;
- repeated query keys need an explicit representation;
- every request needs fresh `query` and `params` objects.

Node's `URLSearchParams` API is useful for query decoding. Take care with the
WHATWG `URL` constructor and a base URL, however: a request target beginning
with `//` is interpreted as a network-path reference. HTTP origin-form targets
use those slashes as pathname text, so parsing must preserve them rather than
turning the first path component into an authority.

## Response helpers are adapters over ServerResponse

The response helpers do not replace Node's response. They set `statusCode`, use
`setHeader`, and eventually call `end`. Returning the same response object makes
helper calls chainable.

Content type should be selected before sending. A caller's explicit header wins
over a helper default. Buffers must not be coerced through strings. JSON encoding
can throw (for example, for a circular object), and that failure belongs in the
same error path as a handler throw.

HEAD is a protocol-level wrinkle: the handler should choose the same status and
headers it would choose for a body-bearing response, but no body bytes may reach
the client.

## Defaults occur only after exhaustion

A 404 means normal dispatch exhausted every eligible layer. A 500 means error
dispatch exhausted every eligible error handler. Neither default should run just
because a handler returned; handlers are allowed to retain ownership while doing
callback-based asynchronous work.

Checking `writableEnded` before defaults and after asynchronous boundaries avoids
many double-response bugs. Once headers have been sent, an error fallback can no
longer safely rewrite them. Normal exhaustion has the same limitation: if a
handler wrote headers and then continued, the only safe default is to end the
response without attempting to install the usual 404 status, headers, or body.
