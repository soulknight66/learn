# Sealed reference tests

These dependency-free tests exercise behaviors intentionally broader than the
public suite: strict HTTP syntax, duplicate handshake fields, canonical and
incremental frame decoding, control-frame constraints, fragmentation with an
interleaved ping, UTF-8 and message limits, close validation, upgrade
read-ahead, a real loopback server, and bounded shutdown.

Run from the repository root:

```bash
ruby -Isealed/reference/lib sealed/reference_tests/run.rb
```

The runner gives every socket read a one-second bound and closes all descriptors
and threads in `ensure` blocks. A pass demonstrates only the cases encoded
here; independent validation remains required.

