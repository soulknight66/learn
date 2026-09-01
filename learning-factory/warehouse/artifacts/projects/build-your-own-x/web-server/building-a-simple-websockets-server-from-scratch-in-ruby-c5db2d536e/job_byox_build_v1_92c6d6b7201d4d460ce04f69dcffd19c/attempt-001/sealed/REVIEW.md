# Sealed implementation review

## Review verdict

The reference is appropriate as a compact teaching implementation and has
meaningful protocol and resource checks. It is not production-ready. The local
sealed suite covers parser and frame edge cases plus connection behavior over
UNIX socket pairs. The sandbox denied TCP loopback binding, so the real TCP
integration case remains explicitly skipped and independent validation is
mandatory.

## Strengths

- Header, frame, message, client, and read-time bounds are distinct.
- Extended lengths are checked before mask or payload acquisition.
- Required handshake fields reject duplicates and ambiguous keys.
- Fragment and close transitions are explicit; control frames can interrupt.
- Client worker registration and removal share one mutex.
- Socket and thread cleanup runs through `ensure` paths.
- No payload or handshake secret is logged.

## Open findings

1. **High — no TLS, authentication, or Origin policy.** Bind to loopback only;
   use a reviewed front end before any broader exposure.
2. **High — blocking callback has no deadline.** A handler can monopolize a
   worker and force last-resort termination during shutdown.
3. **Medium — thread-per-client does not scale broadly.** The admission cap
   bounds damage but does not provide high concurrency.
4. **Medium — failures have no structured reporting hook.** Peer errors are
   intentionally quiet, while unexpected handler errors should reach metrics
   and logs without including payloads.
5. **Medium — shutdown uses `Thread#kill` after its deadline.** Cooperative
   cancellation would provide safer application cleanup.
6. **Medium — TCP behavior is not executed on this host.** UNIX socket pairs
   validate stream logic but not bind, accept, TCP options, or network teardown.
7. **Low — generic HTTP 400 behavior is intentionally minimal.** It does not
   advertise version 13 or distinguish overload from malformed input.

## Required next gate

Run an independent RFC 6455 conformance client and the loopback integration
suite on a network-enabled test host. Resolve the high findings before any
production claim. Do not promote validation labels based on this review alone.

