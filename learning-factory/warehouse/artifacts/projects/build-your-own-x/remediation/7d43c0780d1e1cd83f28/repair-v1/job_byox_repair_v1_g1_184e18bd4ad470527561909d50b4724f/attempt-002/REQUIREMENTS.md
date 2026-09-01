# Mini Express-Style Framework: Requirements

Build a small, dependency-free HTTP framework on top of Node.js. The goal is to
practice ordered middleware dispatch, route matching, error propagation, and safe
request-local state. This is an API-compatibility exercise, not an invitation to
copy Express internals.

The words **must**, **must not**, and **may** are normative. Behavior not described
here is out of scope and is not required.

## Runtime and submission

- Use CommonJS and only Node.js built-in modules.
- Support Node.js 18.17 or newer. The reproducible reference version is Node.js
  20.19.5.
- Put the implementation in `starter/src/index.js`.
- `require('./starter/src/index.js')` must return the `createApplication` function
  directly. Do not require callers to access a named or `default` property.
- Each call to `createApplication()` must return a new, independent application.
- Do not add runtime dependencies.

## Application surface

The value returned by `createApplication()` must be both:

1. a callable `(req, res)` Node HTTP listener, and
2. an object exposing these methods:

   `use`, `get`, `post`, `put`, `patch`, `delete`, `options`, `head`, `all`,
   `listen`, and `handle`.

Calling the application as a listener must be equivalent to calling
`app.handle(req, res)`.

Registration methods must return `app`, so calls can be chained.

### Registration forms

```js
app.use(handler, ...moreHandlers)
app.use('/prefix', handler, ...moreHandlers)

app.get('/path', handler, ...moreHandlers)
app.post('/path', handler, ...moreHandlers)
// The same form applies to put, patch, delete, options, head, and all.
```

- The omitted `use` path defaults to `/`.
- A registration must contain at least one handler.
- Handler arguments may be functions or arrays of functions. Arrays may be
  nested and must retain their left-to-right order.
- Middleware paths must be non-empty strings beginning with `/`. Route paths
  have the same rule except that the standalone pattern `*` is also valid.
- Named route parameters must occupy a whole segment. Their names must match
  `[A-Za-z_][A-Za-z0-9_]*`, and a route pattern must not repeat a parameter
  name.
- A route wildcard must be either the standalone pattern `*` or the whole final
  segment of a slash-prefixed pattern. For example, `/files/*` is valid, while
  `/files*`, `/files/*/more`, and `/:` are invalid.
- Invalid paths or non-function handler values must throw a synchronous
  `TypeError` at registration time.
- Regular-expression paths, arrays of paths, sub-app mounting, and Express
  routers are out of scope.

## Ordering and dispatch

- Registrations form one ordered stack. Matching layers run in registration
  order, even when middleware and routes are interleaved.
- Handlers within one registration run in declaration order.
- Normal handlers receive `(req, res, next)`.
- Error handlers receive `(err, req, res, next)` and are identified by an arity
  of exactly four (`handler.length === 4`).
- In normal mode, error handlers are skipped. After `next(err)` with a non-null,
  non-undefined value, a synchronous throw, or a returned promise rejection,
  normal handlers are skipped until a matching error handler is reached.
- A thrown or rejected reason always enters error mode, even when that reason is
  `null` or `undefined`. The exact reason is preserved and supplied as the first
  argument to an error handler. Implementations must therefore track error mode
  separately from the value carrying the error.
- `next()`, `next(null)`, or `next(undefined)` from a normal handler continues in
  normal mode. The same calls from an error handler mark that error handled and
  continue in normal mode. `next(newError)` with any other value continues in
  error mode with `newError`.
- A handler may finish the response instead of calling `next()`. Dispatch must
  not fabricate another response after `res.writableEnded` becomes true.
- Each invocation of a handler has a once-only continuation: repeated calls to
  the same `next` callback must not run downstream handlers more than once.
- If a handler returns a thenable or promise, a rejection must enter error flow
  as described above, irrespective of its reason. A synchronous throw must do
  so as well.
- `next('route')` and other Express-specific sentinel values are out of scope;
  any non-null, non-undefined argument is an error value.

Returning normally without ending the response or calling `next()` means the
handler has taken ownership of that response. As with Node and Express, such a
handler can leave its request pending; tests will not rely on that mistake.

## Middleware path matching

`app.use` paths are literal, case-sensitive pathname prefixes. The query string
does not participate in matching.

Prefix matches must stop at a path-segment boundary:

- `/api` matches `/api`, `/api/`, and `/api/users`.
- `/api` does not match `/apix` or `/api-v2`.
- `/` matches every pathname.

A single trailing slash on a non-root middleware path must be normalized away,
so `/api/` has the same mount behavior as `/api`. Middleware paths remain
literal; parameter and wildcard syntax has no special meaning for `app.use`. The
framework must leave `req.path` and `req.originalUrl` intact while mounted
middleware runs; path trimming and `baseUrl` are out of scope.

## Route path matching

Route matching is case-sensitive and ignores the query string. A route must
match the entire pathname.

Supported route syntax is deliberately small:

- Literal segments: `/about`, `/v1/items`
- Named parameters occupying a whole segment: `/users/:id`
- One final wildcard: `/files/*` or `*`
- Combinations such as `/users/:id/files/*`

Named parameters match one non-empty segment and are exposed by name.
The final wildcard matches the remaining characters, including `/`, and is
exposed as `req.params['0']`. For example, `/files/a/b` matched by `/files/*`
captures `a/b`. `/files/*` also matches `/files/` and captures the empty string,
but it does not match `/files`. The standalone pattern `*` matches every
pathname and captures the complete pathname, including its leading `/`, as
`req.params['0']`.
A pattern without a wildcard is exact, so `/about` and `/about/` are distinct.

Captured parameter values must be percent-decoded. Literal matching, malformed
escape handling, and decoding must never allow one request to corrupt another
request's state. A decoding failure enters error dispatch just like a thrown
`URIError`. If decoding fails, a later error handler in that same route
registration must be eligible to receive the error without retrying the failed
decode; while it runs, `req.params` is a fresh empty ordinary object because no
complete capture set was produced.

Route methods match the corresponding incoming HTTP method. `all` matches every
method. GET and HEAD are separate for routing purposes: a HEAD request matches
`head` and `all` registrations, not `get` registrations. Automatic OPTIONS and
automatic HEAD route generation are out of scope.

## Request fields

Before dispatch, add these fields to the incoming request:

- `req.originalUrl`: the original request target, including its query string.
- `req.path`: the URL pathname only, always beginning with `/`.
- `req.query`: a new plain object containing decoded query values.
- `req.params`: a new plain object for the currently executing matching
  registration, empty for middleware and populated with captures for a route.

Leading slashes in an origin-form request target are pathname characters, not
an authority marker. In particular, a target beginning `//host/path` has the
pathname `//host/path`; it must not be parsed as a URL reference whose host is
`host` and whose pathname is `/path`.

For `req.query`, decoded keys and values use form-style query semantics: a key
occurring once maps to a string, a repeated key maps to an array in encounter
order, a key without a value maps to `''`, and `+` decodes to a space.

Before invoking a matched middleware registration, replace `req.params` with a
fresh empty object. Before invoking a matched route registration, replace it
with a fresh object containing only that route's captures. All handlers within
one registration see that same params object. Captures from an earlier route
must not remain in later middleware or routes.

The query and params containers must be ordinary objects whose prototype is
`Object.prototype`. Every input-derived key, including `__proto__`, must be
represented as an own, enumerable data property; adding it must not invoke a
prototype setter or change the object's prototype. Repetition checks must
consider own properties rather than inherited names.

`originalUrl`, `path`, `query`, and `params` must be request-local. Concurrent
requests and separate applications must never share these mutable objects.

## Response helpers

Decorate the Node response with these chainable helpers:

- `res.status(code)` sets `res.statusCode` and returns `res`.
- `res.set(name, value)` delegates to Node header semantics and returns `res`.
- `res.type(value)` sets `Content-Type` and returns `res`.
- `res.json(value)` serializes JSON, sends it, and returns `res`.
- `res.send(value)` sends a value and returns `res`.

`res.type` must recognize `json`, `html`, `text`, and `txt` as:

- `application/json; charset=utf-8`
- `text/html; charset=utf-8`
- `text/plain; charset=utf-8`

If the value contains `/`, use it as the media type. Other unknown shorthand
values may fall back to `application/octet-stream`.

`res.json` must use `JSON.stringify`. Unless already set, its content type is
`application/json; charset=utf-8`.

`res.send` behavior:

- Plain objects and arrays delegate to `res.json`.
- Buffers are sent unchanged and default to `application/octet-stream`.
- Strings, numbers, and booleans are sent as their string representation and
  default to `text/plain; charset=utf-8`.
- `null` and `undefined` send an empty body.

An explicitly set `Content-Type` must not be overwritten by `json` or `send`.
All body-producing paths, including the defaults below, must suppress body bytes
for a HEAD request while preserving the chosen status and headers.

## Completion defaults

When normal dispatch reaches the end of the stack without an ended response and
headers have not been sent:

- respond with status `404`;
- set `Content-Type: text/plain; charset=utf-8`; and
- send exactly `Not Found` (or zero body bytes for HEAD).

If normal dispatch exhausts the stack after headers were sent but before the
response ended, simply end the response. Do not try to replace its status or
headers, and do not append the `Not Found` body.

When error dispatch reaches the end without an ended response:

- respond with status `500`;
- set `Content-Type: text/plain; charset=utf-8`; and
- send exactly `Internal Server Error` (or zero body bytes for HEAD).

The 500 response must not include the error message or stack. If headers were
already sent when an unhandled error arrives, end the response without trying to
replace its status or headers.

## Server integration

`app.listen(...args)` must create an `http.Server` using `app` as its listener,
forward the supplied arguments to `server.listen`, and return that server.

No singleton server, route stack, params object, query object, or dispatch cursor
may be shared across application instances or requests.

## Out of scope

Cookies, body parsing, static files, view engines, redirects, content negotiation,
sub-apps, routers, settings, route regexes, optional parameters, and Express
package compatibility beyond this document are not required.
