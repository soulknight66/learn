# Review 01: router boundaries and ownership

Review `flawed-router.js` as if it were proposed for the framework. The author
says it supports mounted middleware and one `:id` parameter per GET route.

Prepare review comments that answer:

1. Which URL can unexpectedly enter a mount, and why?
2. What happens when a captured value contains a malformed percent escape?
3. Which object owns route parameters, and what happens when two async handlers
   overlap?
4. Which fixes belong in matching, which belong in request initialization, and
   which belong at the dispatch error boundary?

Prioritize externally observable correctness and isolation over naming or
formatting. Then run:

```bash
node review_exercises/exercise-01/characterization.js
```

The script reports the delta from the intended observations. Do not change it
until the review is complete.
