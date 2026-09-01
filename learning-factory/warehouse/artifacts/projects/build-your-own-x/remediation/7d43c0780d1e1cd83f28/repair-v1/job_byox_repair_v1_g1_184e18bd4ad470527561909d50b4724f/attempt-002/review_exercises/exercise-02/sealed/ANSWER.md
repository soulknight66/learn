# Review 02 answer

## High-priority findings

1. **Falsy payloads are erased.** `if (!selected)` maps `false`, `0`, and the
   empty string to the same value. Dispatch by type without truthiness
   coercion; `false` and `0` have meaningful textual representations.
2. **Content-Length uses the wrong unit.** String length is measured in UTF-16
   code units, while HTTP framing counts encoded octets. Serialize to a Buffer
   first and use its byte length.
3. **HEAD emits a body.** Choose and serialize the representation exactly as for
   GET so metadata is retained, but call `end()` without the body when
   `req.method` is HEAD.
4. **Status silently repairs invalid input.** `code || 200` turns `0` into 200
   and accepts other invalid values. Require an integer in the supported HTTP
   range and throw before mutating `statusCode`.
5. **JSON changes headers before serialization succeeds.** A circular value or
   unsupported serialization can throw after Content-Type was set. Serialize
   before committing representation headers, then pass the error to framework
   error flow if headers have not been sent.

A coherent sender first validates and serializes into `{ body, contentType }`,
then assigns headers, and finally applies the method-specific wire rule. It
should also guard repeated sends with `headersSent`/`writableEnded`; streaming
values need a separate backpressure-aware path.
