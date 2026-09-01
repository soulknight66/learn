# Review 02: convenient response helpers

Review `flawed-response.js`, which adds chainable `status`, `send`, and `json`
helpers to a response. Assume `setHeader` and `end` behave like their Node.js
HTTP counterparts.

Write prioritized comments about:

- preservation of valid falsy payloads;
- status-code validation;
- the unit used by Content-Length;
- HEAD response semantics; and
- whether serialization errors can leave misleading response state.

Use the smallest coherent remediation rather than adding a special case for
every observed value. The characterization command is:

```bash
node review_exercises/exercise-02/characterization.js
```
