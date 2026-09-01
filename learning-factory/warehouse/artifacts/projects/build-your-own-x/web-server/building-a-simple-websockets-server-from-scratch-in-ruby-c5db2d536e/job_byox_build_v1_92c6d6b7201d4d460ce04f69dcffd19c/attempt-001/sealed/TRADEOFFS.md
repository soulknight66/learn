# Reference tradeoffs

## Thread per admitted connection

Threads make ownership and the blocking socket flow readable, which is useful
for a from-scratch exercise. The hard `max_clients` limit bounds thread count.
The model still incurs one Ruby thread and stack per client and is a poor fit
for very large mostly-idle populations. A selector-driven reactor is the main
alternative described in `alternatives/README.md`.

## Buffering whole messages

The connection buffers a complete logical message so it can validate text and
give the callback a simple value. `max_message_bytes` makes memory finite, but
large binary streaming is impossible. A streaming callback would need explicit
start/chunk/end events and a policy for partially delivered invalid text.

## Strict, small HTTP parser

The upgrade parser accepts only the subset needed for a WebSocket upgrade. It
rejects obsolete folding and ambiguous required fields. This reduces request
smuggling surface but is not a general HTTP server and cannot share a port with
arbitrary HTTP routes without a mature front end.

## No negotiated features

RSV bits always fail because no extension is negotiated. Subprotocol and
permessage-deflate support would expand handshake state and change frame and
message validation. Avoiding them keeps invariants local and prevents accidental
compression-bomb exposure.

## Immediate close under saturation

Closing excess accepted sockets is bounded and deterministic but gives clients
little diagnostic information and no fairness. A production listener could
apply a small admission timeout, metrics, source-level quotas, or upstream load
shedding while still refusing unbounded work.

## Forced bounded shutdown

Closing sockets normally wakes workers. The reference additionally terminates
a worker that outlives the shared deadline. That makes tests and process exit
bounded, but asynchronous thread termination can interrupt application cleanup.
A production design should use cooperative cancellation and callbacks with
their own time budgets.

