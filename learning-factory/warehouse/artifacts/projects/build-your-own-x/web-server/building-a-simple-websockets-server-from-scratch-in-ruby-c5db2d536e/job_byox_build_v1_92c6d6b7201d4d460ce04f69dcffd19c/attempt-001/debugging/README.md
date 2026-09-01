# Debugging exercise 01: the vanishing first message

A learner's handshake test passes when the client waits for `101`, but the
first message vanishes when a client sends its upgrade and first frame in one
TCP write. Their reader repeatedly appends `readpartial(4096)` until it sees
`\r\n\r\n`, parses the header prefix, and returns only the parsed headers.

Reproduce the failure with a socket pair. Identify which layer owns bytes after
the header boundary, propose the smallest API change that preserves them, and
add a regression test where the boundary falls in the middle of a read buffer.

The sealed answer for this exercise is isolated under the evaluator's sealed
tree; no answer is present here.

