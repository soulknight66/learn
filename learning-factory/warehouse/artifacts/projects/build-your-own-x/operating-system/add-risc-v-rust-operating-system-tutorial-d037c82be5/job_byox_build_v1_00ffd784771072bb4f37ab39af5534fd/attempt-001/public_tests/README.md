# Public tests

This crate exercises the stable learner-facing API in `starter/`. Run it from
the repository root:

```bash
cargo test --manifest-path public_tests/Cargo.toml
```

The tests are examples, not a full specification. They intentionally omit many
failure-atomicity checks, exhaustion cases, malformed paths, upper canonical
Sv39 addresses, and long state sequences. Derive those cases from
`REQUIREMENTS.md` rather than matching only the examples here.
