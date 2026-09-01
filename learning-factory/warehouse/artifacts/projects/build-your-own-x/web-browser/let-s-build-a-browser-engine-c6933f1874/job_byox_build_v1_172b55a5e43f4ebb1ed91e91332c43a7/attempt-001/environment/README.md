# Environment

Expected tools:

- stable Rust edition 2021 (`rustc` and `cargo`);
- no network access and no third-party crates;
- a POSIX-like shell only for invoking Cargo.

Commands from the repository root:

```text
cargo fmt --manifest-path starter/Cargo.toml -- --check
cargo test --manifest-path starter/Cargo.toml
cargo test --manifest-path sealed/reference/Cargo.toml
```

The generation host did not provide Rust tooling. See `VALIDATION.md` for exact observed results; this artifact is therefore labeled `PARTIAL` pending independent compilation and tests.
