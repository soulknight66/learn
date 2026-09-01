# Reference design answers

## 1. Upgrade read-ahead

The HTTP reader accumulates bytes until the first CRLF-CRLF boundary. It parses
only through that boundary and stores every trailing byte in the request
object. `take_remainder` transfers those bytes exactly once to the frame
decoder. This prevents a coalesced first frame from being discarded.

## 2. Early length rejection

Once the decoder has two base bytes and the indicated two- or eight-byte
extended length, it knows the advertised payload size. It applies the frame
limit before waiting for a mask key or any payload. The implementation also
checks the high bit and canonical form. A limit breach takes precedence over a
noncanonical encoding when the decoded value already breaches the configured
resource boundary.

## 3. Fragment state

`@fragment_opcode == nil` means idle. In that state, text or binary may begin;
a continuation is illegal. A non-final text/binary frame saves its opcode and
starts `@message`. While the opcode is present, only continuation data frames
may extend the message. Ping, pong, and close are legal in either state and do
not alter fragment state. A final continuation completes and clears it.

## 4. UTF-8 timing

A UTF-8 code point can straddle fragment boundaries, so validating fragments
separately rejects valid messages. The reference assembles bounded bytes and
validates the completed text message once. Invalid completed text produces
close code 1007.

## 5. Write ownership

Only the connection worker writes protocol frames. The server shutdown path
closes descriptors but does not emit a frame. That preserves frame byte
serialization without adding a write mutex. A future design with timers or
broadcast writers would need a per-connection output owner or synchronized
queue.

## 6. Saturation

The reference accepts and immediately closes a socket if no worker slot is
available. This keeps the accept backlog moving and creates neither an
unbounded Ruby queue nor an extra thread. It is intentionally simple and not
fair: a production service might send a small HTTP rejection before upgrade,
rate-limit by source, or use a fixed worker reactor.

## 7. Shutdown contract

`stop` first marks the service stopped under a mutex, closes the listener and
all registered client sockets, then joins the accept and client threads against
one monotonic deadline. A last-resort thread termination keeps the API bound;
that is suitable for this isolated challenge but called out as a production
review concern. Tests should synchronize through real socket readability and
`Thread#join(timeout)`, never assume that a sleep means a worker reached a
particular state.

## 8. Failure classes

`HandshakeError` and `ProtocolError` describe peer-scoped input failures.
EOF and common socket errors are ordinary disconnects. `LimitError` is a
protocol close 1009. Callback and unexpected internal exceptions indicate a
server/application defect; the worker's `ensure` still unregisters and closes
the socket, and the listener stays alive. Operational code should report such
defects through a structured error hook.

## 9. Close reflection

A close payload may be empty, but never exactly one byte. A present code must be
allowed on the wire: 1000–1014 excluding 1004, 1005, and 1006, or 3000–4999.
The remaining bytes must form valid UTF-8. Only after these checks does the
reference echo the payload, and a boolean guard prevents a second close frame.

## 10. Evidence before exposure

At minimum: normative conformance cases from an independent harness; supported
Ruby-version CI; TCP integration on a host that permits loopback; sustained
load and slow-peer tests with recorded resource ceilings; race and shutdown
stress; external security review; TLS termination; authentication and origin
policy; observability without payload leakage; and documented deployment,
rollback, and incident procedures. None of that evidence is established by
this artifact.

