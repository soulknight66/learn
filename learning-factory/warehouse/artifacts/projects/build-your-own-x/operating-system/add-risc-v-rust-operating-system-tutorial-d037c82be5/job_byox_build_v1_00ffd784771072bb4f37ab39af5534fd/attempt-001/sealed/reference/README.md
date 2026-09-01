# Sealed reference implementation

This safe, standard-library-only Rust crate implements the complete public
contract from `REQUIREMENTS.md`. It is evaluator material, not learner-visible
guidance. The implementation models semantics on a host; it does not contain a
boot path, privileged RISC-V instructions, drivers, or persistence.

When a Rust toolchain is available, exercise it through the separate sealed
test crate:

```bash
cargo test --manifest-path sealed/reference/Cargo.toml
cargo test --manifest-path sealed/reference_tests/Cargo.toml
```

The generating host lacked `cargo` and `rustc`, so this source has not been
compiled in this artifact and must be independently validated.
