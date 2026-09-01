# Design Questions

Use these questions while planning and reviewing an implementation. This root
file is the read-only assessment prompt; record answers in
`starter/DESIGN_QUESTIONS.md`. The public contract fixes externally observable
behavior, but it intentionally does not fix the internal architecture.

## Application and registration

1. Where will an application's ordered layers live so that two apps cannot share
   registrations?
2. What normalized shape will represent middleware and route layers?
3. Will handler arrays be flattened at registration or during every request?
4. Which invalid patterns can be rejected early, before a server starts?
5. How will route literal characters be kept literal if a regex is involved?

## Dispatch

1. Which values form the per-request dispatch state?
2. How does the dispatcher move between handlers inside one layer and later
   layers without skipping registration order?
3. How will normal mode and error mode select handlers by arity?
4. What happens if `next()` is called synchronously before the current handler
   returns?
5. How will one invocation's `next` become inert after its first call?
6. How will a returned thenable be observed without automatically advancing when
   it fulfills?
7. If a handler calls `next()` and then its returned promise rejects, how will a
   stale rejection be prevented from dispatching the stack a second time?
8. At what exact point is it valid to emit a 404 or 500 default?

## Matching and URL fields

1. Can middleware prefix matching be expressed without accidentally matching
   `/api-v2` for the mount `/api`?
2. How will exact routes distinguish `/about` from `/about/`?
3. What does the final wildcard capture for nested paths?
4. Where are percent-decoding failures handled?
5. When should `req.params` be replaced so one matching route cannot leak names
   into the next?
6. How will repeated query keys preserve encounter order?

## Responses and errors

1. Should helpers be installed once on a prototype or on each response, and what
   tradeoffs does that choice create?
2. How will helpers detect an already explicit `Content-Type` regardless of
   header casing?
3. How will string byte length differ from JavaScript string length if a content
   length is added?
4. Where should JSON serialization errors enter middleware error flow?
5. How will HEAD suppress bytes for helpers, defaults, and direct Node response
   usage?
6. What safe action remains when an unhandled error occurs after headers have
   already been sent?

## Verification

1. Which tests prove segment-boundary matching rather than simple prefix
   matching?
2. Which tests prove registration order when routes and middleware are mixed?
3. Can two deliberately interleaved requests expose a global dispatch cursor or
   params object?
4. Do tests cover both synchronous throws and delayed promise rejections?
5. Can a double-`next` handler cause a downstream counter to increment twice?
6. Does a HEAD assertion inspect body bytes, rather than trusting handler intent?
