# Concepts

## HTTP is only the doorway

A WebSocket connection begins as an HTTP/1.1 request. The server verifies a
specific set of headers and replies with status 101. After the blank line, the
same TCP stream changes interpretation: subsequent bytes are WebSocket frames,
not HTTP messages. A parser must therefore consume exactly the upgrade bytes
and preserve any following bytes.

## TCP supplies a stream, not records

One `read` need not correspond to one frame. A frame header can arrive across
several reads, and several frames can arrive together. An incremental decoder
keeps a byte buffer, peeks only when enough bytes exist, validates advertised
lengths before waiting or allocating, and removes bytes only for a complete
frame.

## Frames and messages differ

A logical message may occupy one data frame or an initial text/binary frame
followed by continuation frames. Ping, pong, and close frames can appear in the
middle. This makes message assembly a state machine rather than a concatenation
shortcut. Frame limits and message limits are separate defenses.

## Masking establishes direction

Clients mask payload bytes with a four-byte key; servers normally do not.
Masking is repeating XOR, so the payload byte at index `i` uses key byte
`i mod 4`. It is not encryption or authentication. Directional validation is a
protocol invariant that also catches peers speaking the wrong role.

## Control frames interrupt data flow

Control frames are final, carry at most 125 bytes, and have their own rules.
Ping should be answered without waiting for a fragmented message to finish.
Close begins a handshake: echo a valid peer close once, then stop consuming
application traffic.

## Concurrency needs ownership

A thread-per-client server is understandable but still needs a hard client
bound, synchronized socket/thread registries, deterministic shutdown, and
failure containment. One thread should own writes to a connection, or writes
must be serialized, because interleaved frame bytes corrupt both responses.

## Bounds are part of correctness

Header size, frame size, assembled message size, client count, and timeouts are
not optional tuning knobs. Each bounds a different resource. Length fields must
be checked before allocation, and cleanup paths must run for EOF, timeout,
malformed input, callbacks, and server shutdown.

