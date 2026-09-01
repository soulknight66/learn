# Reference tradeoffs

## A deliberately small path language

Routes are compiled to regular expressions for fast repeat matching, but only after parsing the
documented segment grammar. This avoids runtime dependencies and regex injection while intentionally
excluding optional segments, user-provided regexes, and Express `path-to-regexp` compatibility.
Middleware has a separate literal matcher rather than sharing route syntax; the duplication keeps
mount semantics obvious and prevents `:` or `*` from changing meaning unexpectedly.

## Callback-driven dispatch

The dispatcher resumes only when a handler calls its once-only `next` or a returned thenable rejects.
This supports both timer/callback middleware and async functions without guessing when a handler has
taken ownership of a response. Synchronous continuation forms a recursive call chain, which is simple
and preserves registration order, at the cost of possible stack pressure for an unrealistically huge
chain of middleware that all call `next` synchronously.

Flattening nested handlers makes dispatch uniform. The request-local registration-to-params map adds
a small allocation and lookup, but it preserves the important distinction between sharing params
inside one registration and replacing them at the next registration. When capture decoding fails,
the map retains a fresh empty object for that matched registration. This makes failure state
slightly more explicit and prevents route-local error handlers from retriggering the same decoder.

## Plain objects without prototype mutation

Null-prototype dictionaries would naturally avoid prototype pollution, but the contract requires
ordinary objects. Defining every input key as an own data property retains the expected prototype
and safely represents special keys. This is slightly more verbose than assignment and marginally
more expensive during parsing, in exchange for deterministic semantics for adversarial names.

## Direct request-target parsing

Splitting the origin-form target avoids WHATWG URL behavior that interprets a leading `//` as an
authority. It also leaves route matching on the raw encoded pathname. Query decoding is delegated to
the built-in `URLSearchParams`; repeated fields use the compact scalar-then-array representation
rather than making every value an array.

Only captured route values are percent-decoded. A malformed captured value raises the native
`URIError` into ordinary error middleware. If unhandled, it intentionally receives the same opaque
500 as every other error rather than introducing an undocumented 400 policy.

## Predictable rather than broad response behavior

The helpers implement only the specified value classes and a small MIME shorthand table. Exact
content lengths make HEAD and default responses observable and deterministic. Statuses that forbid
body bytes retain their selected content type but omit content-length and transfer framing. GET does
not implicitly serve HEAD, OPTIONS is not synthesized, and no content negotiation is attempted. For
an error after headers have been sent, ending the stream is the only safe generic action; changing
the already-committed response would be invalid.

These choices favor a teachable, testable control flow over Express feature parity. Production work
would additionally need request-size controls, body parsing, richer lifecycle and abort handling,
observability, configurable error policy, and defenses for extreme stack and route counts.
