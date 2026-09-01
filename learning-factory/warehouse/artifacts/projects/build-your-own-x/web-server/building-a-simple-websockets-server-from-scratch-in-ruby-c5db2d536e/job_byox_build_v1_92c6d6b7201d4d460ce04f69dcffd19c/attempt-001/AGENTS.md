# Working agreement

Work only in this challenge directory and treat `starter/` as the learner-owned
implementation. Do not read `sealed/`; it contains evaluator and reference
material and is not part of the learner view.

Preserve the public API named in `REQUIREMENTS.md`. Prefer deterministic,
dependency-free code compatible with Ruby 2.5 or newer. Network tests must bind
to `127.0.0.1` and an operating-system-assigned port, use bounded waits, and
always close sockets and threads in `ensure` blocks.

Do not add real credentials, private keys, access tokens, captured traffic, or
third-party tutorial text. Treat bytes from a socket as hostile: bound headers
and frames before allocating, validate state transitions, and do not log raw
application payloads by default.

Run the public suite from `starter/`:

```bash
ruby -Ilib ../public_tests/run.rb
```

Passing public checks is useful feedback, not proof of full protocol
correctness or production readiness.

