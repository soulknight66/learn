# Sealed reference tests

These evaluator-only integration tests cover boundaries deliberately absent
from the public smoke suite: failed-walk rollback, upper-canonical addresses,
shared page-table reclamation, wrong-allocator atomicity, path grammar, range
overflow, and longer scheduler transitions.

Run with:

```bash
cargo test --manifest-path sealed/reference/Cargo.toml
cargo test --manifest-path sealed/reference_tests/Cargo.toml
```

No successful run is recorded because the generation host had no Rust
toolchain. Independent execution remains required.
