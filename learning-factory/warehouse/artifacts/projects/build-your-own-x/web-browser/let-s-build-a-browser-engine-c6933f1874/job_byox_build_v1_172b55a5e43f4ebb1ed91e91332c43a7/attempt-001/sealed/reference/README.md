# Sealed reference implementation

This dependency-free Rust crate implements the complete learner API. It keeps protocol framing, decoding, DOM construction, styling, layout, and painting as separate typed stages. Its Cargo manifest runs both the public suite and the sealed conformance suite.

Intended validation commands from the repository root:

```text
cargo fmt --manifest-path sealed/reference/Cargo.toml -- --check
cargo test --manifest-path sealed/reference/Cargo.toml
```

The generation host had no Rust toolchain, so these commands could not be executed here. This is reference material, not a claim of production readiness.
