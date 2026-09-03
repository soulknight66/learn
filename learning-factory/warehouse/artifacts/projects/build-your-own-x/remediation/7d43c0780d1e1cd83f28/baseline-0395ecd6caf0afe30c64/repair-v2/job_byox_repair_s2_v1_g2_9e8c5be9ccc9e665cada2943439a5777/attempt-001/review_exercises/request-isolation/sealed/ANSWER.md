# Review answer

Severity: high correctness and cross-request data-isolation flaw.

`activeIdentifier` is process-global mutable state. Single-threaded execution does not make the
handler atomic: the `await` yields to the event loop. Request A can store `A` and pause; request B
then stores `B`; when A resumes it reports B's identifier. In a real service this can disclose one
client's data to another.

A deterministic test should send A with a longer delay, wait until A has entered the handler, then
send B with no delay. Both responses must contain matching `startedAs` and `finishedAs` values; the
broken version makes A fail.

Keep the identifier in lexical request-local state:

```js
async function handleJob(req, res) {
  const identifier = req.params.id;
  await new Promise((resolve) => setTimeout(resolve, Number(req.params.delay)));
  res.json({ startedAs: identifier, finishedAs: identifier });
}
```
