# TinyWS: build a WebSocket server in Ruby

TinyWS is a dependency-free systems-programming challenge. You will turn the
incomplete code in `starter/` into a small RFC 6455 WebSocket server while
working directly with TCP sockets, HTTP upgrade bytes, masked frames, message
fragmentation, and bounded concurrency.

This is an independently written learning artifact. The linked catalog article
was not copied and is not needed to complete the work.

## What you will build

The finished server accepts an HTTP/1.1 WebSocket upgrade, validates it, reads
incremental client frames, echoes complete text or binary messages, answers
ping frames, performs a close handshake, and isolates failures to one
connection. It intentionally uses only Ruby's standard library.

## Progressive path

1. **Handshake primitives** — complete `TinyWS::Handshake.accept_for` and the
   request validation in `TinyWS::HTTPUpgrade`.
2. **Wire frames** — implement payload lengths, masking, incremental buffering,
   and protocol validation in `TinyWS::FrameDecoder` and `TinyWS::Frame`.
3. **Connection state** — assemble fragmented messages and handle ping, pong,
   and close control frames in `TinyWS::Connection`.
4. **Network service** — finish `TinyWS::Server` with bounded client slots,
   clean shutdown, timeouts, and per-client error containment.
5. **Hardening** — use the adversarial, debugging, review, and benchmark prompts
   after the public checks pass.

Read `REQUIREMENTS.md` before coding. `CONCEPTS.md` explains the protocol model,
while `DESIGN_QUESTIONS.md` asks you to justify decisions without revealing a
reference answer.

## Quick start

```bash
cd starter
ruby -Ilib ../public_tests/run.rb
ruby -Ilib bin/tiny_ws --host 127.0.0.1 --port 8080
```

The starter tests are expected to report failures until the TODOs are
implemented. No gems are required. See `environment/README.md` for the tested
runtime and `public_tests/README.md` for test conventions.

## Safety boundary

Bind to loopback while learning. This challenge does not claim production
readiness, TLS support, HTTP authentication, extension negotiation, or
multi-process resilience. Independent validation is required even if all local
checks pass.

