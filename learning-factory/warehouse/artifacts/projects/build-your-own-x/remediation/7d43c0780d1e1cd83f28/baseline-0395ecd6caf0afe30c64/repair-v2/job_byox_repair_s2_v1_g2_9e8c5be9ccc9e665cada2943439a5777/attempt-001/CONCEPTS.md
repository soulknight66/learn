# Concepts

## HTTP is a state machine over a byte stream

Node's parser turns socket bytes into `IncomingMessage` and `ServerResponse` objects, but application
code still owns ordering: status and headers precede body bytes, some statuses prohibit bodies, and
one request may arrive while many others are awaiting I/O. `Content-Length` counts bytes, not
JavaScript characters.

## Middleware is controlled continuation

`next` represents “run the remainder of the pipeline.” Awaiting it gives onion-shaped execution:
setup runs on the way in and cleanup runs on the way out. A per-dispatch index prevents one
continuation from being invoked twice. Decide explicitly what happens when middleware neither sends
a response nor delegates.

## Routing has two separate decisions

First determine whether a pathname matches a pattern; then determine whether the HTTP method is
allowed. Keeping these decisions separate makes 404, 405, automatic `OPTIONS`, and `Allow` behavior
testable. A nonempty `Allow` set means 405 only when the current method is absent from it; a handler
for a supported method can still fall through to 404. Decode only captured values and treat
malformed percent escapes as client errors.

## Streams require hostile-input thinking

The body may arrive in many chunks, be empty, exceed its declared size, omit a size, error, or abort.
A body limit must be enforced while bytes arrive, not after concatenating everything. Listener
cleanup matters because every request owns a distinct stream. Before and after attaching listeners,
inspect terminal stream state: an abort or error might have occurred while earlier middleware was
awaiting work.

## Concurrency means interleaving

Node normally executes JavaScript on one event-loop thread, yet requests overlap whenever handlers
await timers, sockets, or files. Module-level `currentRequest` variables are therefore unsafe even
without threads. Store request-specific values on the request object or in lexical variables. To
test this deterministically, pause one request at a gate until a second request reaches the same
critical section.

## Error boundaries are protocol boundaries

Before headers are sent, a framework can choose a clean error representation. After bytes are on the
wire, changing the status is impossible; terminating the connection is safer than appending a JSON
error to a partial payload. Internal exception text should not be exposed to remote clients.
