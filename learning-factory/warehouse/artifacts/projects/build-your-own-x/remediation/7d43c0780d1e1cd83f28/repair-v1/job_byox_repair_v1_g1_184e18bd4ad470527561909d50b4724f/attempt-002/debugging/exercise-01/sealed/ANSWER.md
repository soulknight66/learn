# Exercise 01 answer

`dispatch` is passed directly as `next`, so every call from a handler owns a
fresh traversal attempt. The global index prevents already-consumed handlers
from running again, but it does not prevent a second traversal from reaching
the end and calling `done` again. Checking only `index` or `res.writableEnded`
would hide one symptom without establishing who may advance control flow.

Create a `nextOnce` closure for each selected handler. It records whether that
specific invocation has advanced and ignores every later call. Synchronous
throws should be sent through the same closure, so a throw after `next()` is
also treated as a late second signal. The complete example is in
`fixed-router.js`.

After applying that pattern, `node debugging/exercise-01/test.js` should print
one PASS line. This answer has not been executed in the build environment when
Node.js is unavailable.
