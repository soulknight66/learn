# Exercise 02: response framing disagrees with the payload

`src/respond.js` is a small response writer used after routing. ASCII GET
responses appear correct, but clients report framing trouble for other valid
requests.

Run:

```bash
node debugging/exercise-02/test.js
```

Change only `src/respond.js`. Keep JSON serialization and the default status,
while ensuring the advertised representation length is correct and requests
whose method is HEAD do not emit body bytes. Do not remove useful representation
headers merely because HEAD has no wire body.
