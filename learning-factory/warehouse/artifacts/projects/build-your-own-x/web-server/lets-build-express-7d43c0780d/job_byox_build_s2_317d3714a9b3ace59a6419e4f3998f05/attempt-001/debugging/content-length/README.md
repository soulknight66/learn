# Exercise: truncated Unicode response

The server in `broken.js` works for ASCII but clients can report a truncated or malformed response
for some Unicode strings.

1. Start the server on an ephemeral loopback port from a test.
2. Request `/`.
3. Assert both the complete UTF-8 payload and the framing header.
4. Identify why the header and emitted bytes disagree.
5. Correct the smallest relevant expression and close the test server.
