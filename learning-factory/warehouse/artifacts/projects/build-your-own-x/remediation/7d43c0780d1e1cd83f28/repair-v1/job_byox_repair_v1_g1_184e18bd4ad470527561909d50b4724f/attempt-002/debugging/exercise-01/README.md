# Exercise 01: the callback that finishes twice

The tiny dispatcher in `src/router.js` walks a stack of Connect-style
middleware. A regression report says that the completion callback can run more
than once when middleware is re-entrant.

Reproduce the issue from the repository root:

```bash
node debugging/exercise-01/test.js
```

Change only `src/router.js`. Preserve these intended behaviors:

- handlers execute in registration order;
- any non-null, non-undefined `next(error)` value skips normal handlers and
  selects four-argument error handlers;
- a thrown error follows the same error path;
- completion receives an otherwise-unhandled error; and
- one invocation of a handler may advance the dispatcher at most once.

Do not special-case the test middleware or rely on response state. Explain why
the defect is a control-flow ownership bug, not merely a counter bug.
