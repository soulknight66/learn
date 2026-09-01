# Reference design

The reference is a dependency-free CommonJS module whose direct export is
`createApplication`. Each factory call closes over a new registration stack and returns a function
that delegates to its own `handle` method, so the same value works with `http.createServer` and also
offers the required Express-style methods.

## Registration and matching

Registration is deliberately front-loaded and deterministic. Paths are validated and handlers are
recursively flattened before anything is appended to the stack, preventing a failed registration
from installing a partial route. Cyclic arrays and non-functions produce synchronous `TypeError`s.

Middleware and routes use separate matchers because their languages are different:

- middleware paths normalize one trailing slash, then remain literal prefixes with a
  segment-boundary check;
- route paths compile once to anchored regular expressions supporting escaped literals, whole
  `:name` segments, and one whole final `*` segment;
- capture names are recorded beside the expression, then capture values are decoded for each
  request with `decodeURIComponent`.

The flattened entries retain a shared registration identity. A request-local map associates that
identity with its matched params object. A successful decode caches the complete capture object. If
capture materialization throws, the dispatcher caches a fresh empty object before entering error
mode; a later error handler in that registration can therefore run without repeating the failed
decode. Consequently, handlers from one registration see the same object, while the next matching
middleware or route receives a new ordinary object as required.

## Request-local state

The request target is split directly at the first `?`. This preserves leading double slashes as
pathname data instead of accidentally treating them as a URL authority. `originalUrl` remains the
unaltered target and `path` remains percent-encoded. A new `URLSearchParams` instance supplies query
decoding; the reducer stores the first value as a string and promotes it to an array on repetition.

`query` and `params` have `Object.prototype`, matching the public contract. Input-derived properties
are installed with `Object.defineProperty` as enumerable writable data properties. That mechanism
allows names such as `__proto__`, `constructor`, and `toString` without invoking inherited setters
or confusing inherited values with prior input.

All routing cursors, continuation flags, params maps, and request decorations are allocated inside
one `handle` invocation. The only long-lived data are immutable-ish registration descriptions in
the application-specific stack.

## Dispatch and errors

Dispatch walks one ordered stack and carries error mode independently from the error value. A private
symbol represents normal mode, so a thrown or rejected `undefined`, `null`, `false`, `0`, or empty
string is still an error, while `next(null)` and `next(undefined)` retain their specified normal-flow
meaning.

Each handler receives a closure-local once flag. Its first `next` resumes at the following stack
index; later calls do nothing. Synchronous throws resume error dispatch, and returned thenables gain
a rejection continuation. Resolution does not imply `next`: a handler that neither responds nor
continues owns the pending response, matching Node middleware conventions. Error middleware is
recognized only by `handler.length === 4`.

Exhausting normal or error mode selects the fixed 404 or 500 representation. If a response is
already ended, dispatch stops. If headers were sent before an unhandled error, the implementation
ends the response without attempting an invalid status/header rewrite.

## Responses and servers

Response helpers close over the current request so HEAD suppression applies consistently. `send`
normalizes supported values to a `Buffer`, chooses a default type only when none was explicitly set,
sets an exact content length, and calls `end` without bytes for HEAD. `json` delegates serialization
to `JSON.stringify` and then to `send`. Statuses that prohibit entity bodies are ended without entity
framing headers while preserving the selected content type.

`listen` creates a fresh `http.Server` around the callable application and forwards all listen
arguments. It stores no singleton server.

## Verification

The sealed tests use `node:test` and real ephemeral loopback servers. They exercise every method,
ordering and prefix boundaries, route grammar and decoding failures, params replacement, special
object keys, error-mode transitions (including falsy and nullish reasons), promise rejection,
once-only continuation, response helpers, HEAD behavior, application isolation, and overlapping
requests synchronized by an explicit barrier. The HTTP helper applies in-process timers, a
response-size ceiling, and abort/error handling. Those timers bound yielding operations only; the
documented outer runner supplies a process-group wall-clock deadline for untrusted synchronous code.
