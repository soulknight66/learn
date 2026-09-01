# TinyWS requirements

The challenge target is a dependency-free Ruby implementation of the server
side of the core RFC 6455 protocol. The required public constants live under
the `TinyWS` module. Do not change method names or return shapes used by public
tests.

## 1. Upgrade request

`TinyWS::HTTPUpgrade.read(io, max_bytes:, timeout:)` must incrementally read
until the first `\r\n\r\n`, reject bare-LF input, EOF, timeout, and oversized
headers, and return a request object with `method`, `target`, `version`, and
case-insensitive headers. Reject obsolete folded header lines and malformed
header names. Duplicate ordinary headers must not silently overwrite one
another; comma-combining is acceptable for token-list fields.

`TinyWS::HTTPUpgrade.validate!(request)` accepts only:

- `GET` with HTTP/1.1;
- an `Upgrade` header whose case-insensitive value is `websocket`;
- a `Connection` token list containing `Upgrade`;
- `Sec-WebSocket-Version: 13`; and
- exactly one `Sec-WebSocket-Key` that is canonical Base64 for 16 decoded bytes.

Invalid upgrades raise `TinyWS::HandshakeError` and must not produce a `101`
response. `TinyWS::Handshake.accept_for(key)` returns the Base64-encoded SHA-1
of the ASCII key concatenated with the RFC 6455 GUID. `response_for(request)`
returns a complete `101 Switching Protocols` response using CRLF endings.

## 2. Frames

`TinyWS::Frame` has readers `fin`, `opcode`, and `payload`. Its class method
`encode(opcode:, payload:, fin: true, mask: false, masking_key: nil)` returns a
binary string. It supports payload length forms 0..125, 16-bit, and 63-bit
unsigned; rejects values beyond the configured protocol range; and applies the
four-byte XOR mask when requested.

`TinyWS::FrameDecoder.new(require_mask:, max_frame_bytes:)` exposes
`feed(bytes)` and `next_frame`. Feeding may split a frame at any byte or include
multiple frames. `next_frame` returns `nil` until complete and consumes exactly
one frame when complete. Before allocation or waiting for payload bytes it must
reject:

- nonzero RSV bits (no extensions are negotiated);
- reserved opcodes;
- unmasked client frames when `require_mask` is true;
- noncanonical extended lengths;
- a 64-bit length with its high bit set;
- frames larger than `max_frame_bytes`; and
- fragmented or oversized control frames.

Violations raise `TinyWS::ProtocolError`, which carries a WebSocket close code.

## 3. Connection state machine

`TinyWS::Connection.new(io, max_frame_bytes:, max_message_bytes:, read_timeout:)`
provides `run { |type, payload| ... }`. It consumes masked client frames and:

- yields complete text messages as `[:text, payload]` and binary messages as
  `[:binary, payload]` through the block arguments;
- validates UTF-8 only after a complete text message is assembled;
- permits control frames between fragments;
- answers ping immediately with a pong carrying identical payload;
- ignores pong at the application layer;
- rejects invalid continuation sequences and messages beyond the bound;
- validates close payload length, close codes, and UTF-8 reason text; and
- sends at most one close frame before returning.

The block's return value becomes the echoed response payload. `nil` means no
application response. The response uses the input message opcode. Protocol
errors should attempt a close with the error's code, then terminate that
connection without taking down the listening server.

## 4. Server and command line

`TinyWS::Server.new(host:, port:, max_clients:, max_header_bytes:,
max_frame_bytes:, max_message_bytes:, handshake_timeout:, read_timeout:)`
provides:

- `start`, which binds and begins accepting;
- `port`, which reports the selected port (including when configured with 0);
- `stop`, which is idempotent, stops acceptance, closes active sockets, and
  joins worker threads within a bounded interval; and
- `serve_forever`, a blocking convenience wrapper.

Each accepted socket is upgraded before `TinyWS::Connection` runs. At most
`max_clients` connection workers may be active. A saturated server closes or
rejects excess connections without spawning an unbounded queue. Shared
bookkeeping must be synchronized. The executable accepts `--host`, `--port`,
and the documented limit options, traps `INT`/`TERM`, and binds to loopback by
default.

## 5. Quality constraints

- Use socket byte strings (`Encoding::BINARY`) internally.
- Use bounded reads and limits supplied by callers.
- Do not use a shell, external commands, gems, or WebSocket libraries.
- Do not print payloads or handshake keys to logs.
- Preserve the first protocol failure; avoid retry loops on malformed input.
- All local tests and processes must terminate without manual cleanup.

TLS, permessage-deflate, subprotocol selection, HTTP keep-alive, authentication,
browser UI, and production deployment are explicitly out of scope.

