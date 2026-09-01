# Environment

The artifact is dependency-free and targets Ruby 2.5 or newer on a POSIX-like
host. A normal deployment needs TCP loopback support.

Observed while generating this pack:

- `ruby --version`: `ruby 2.5.9p229 (2021-04-05 revision 67939) [x86_64-linux]`
- `minitest/autorun`: unavailable (`LoadError`)
- TCP loopback bind in this sandbox: blocked (`Errno::EPERM`)
- local `Socket.pair` transport: available and used by connection tests
- external gems: neither required nor installed for this artifact
- upstream article access: not attempted

The suites therefore use `public_tests/test_harness.rb`, a tiny local runner.
Tests bind only to `127.0.0.1` and should use ephemeral ports. A container is
not necessary. If your Ruby lacks OpenSSL, that is acceptable: the handshake
uses `Digest::SHA1`, `Base64`, and `Socket` from the standard library.
