# Adversarial evaluation notes

This directory contains evaluator-facing test themes, not learner solutions or claimed results.

Independent tests should vary:

- malformed and overlong percent escapes, encoded slashes, duplicate parameters, and wildcard edges;
- method/path combinations for 404, 405, HEAD fallback, explicit HEAD, and OPTIONS;
- prefix lookalikes such as `/api`, `/api/`, `/apiary`, and repeated slashes;
- UTF-8 byte lengths, empty bodies, scalar JSON, invalid UTF-8, suffix media types, and encodings;
- missing, huge, inconsistent, chunked, aborted, and errored body streams;
- synchronous throws, rejected promises, repeated `next`, double sends, and errors after headers;
- dozens of interleaved requests with distinct parameters and bodies;
- server close behavior and unhandled rejection detection.

Any adversarial implementation or result belongs in validator-controlled evidence, not here.
