# Sealed reference implementation

This directory contains an independently authored, dependency-free reference
for the TinyWS challenge. It targets clarity and deterministic bounds rather
than production deployment. The entry point is `lib/tiny_ws.rb`; the executable
is `bin/tiny_ws`.

Run its sealed suite from the repository root:

```bash
ruby -Isealed/reference/lib sealed/reference_tests/run.rb
```

The implementation supports the core server-side RFC 6455 handshake, masked
client frames, unmasked server frames, fragmented text and binary messages,
ping/pong, close validation, a bounded thread-per-connection service, and
coordinated shutdown. TLS, extensions, and subprotocols remain intentionally
out of scope.

