# Starter crate

Implement the `todo!()` sites in `src/process.rs`, `src/memory.rs`, and
`src/fs.rs`. The supplied types and signatures are the compatibility surface
used by external tests. Private representation changes and private helpers are
welcome; adding dependencies, unsafe code, or target-specific behavior is not.

Start with one subsystem by passing a name filter after the command, for
example:

```bash
cargo test --manifest-path public_tests/Cargo.toml process_
```

The public suite is only a smoke test. Add unit tests within the starter crate
to cover every error path and post-error invariant.
