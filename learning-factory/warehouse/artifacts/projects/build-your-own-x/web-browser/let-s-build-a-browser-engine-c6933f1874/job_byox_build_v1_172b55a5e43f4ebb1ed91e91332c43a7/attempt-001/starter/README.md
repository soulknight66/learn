# Starter crate

This crate defines the required API. Replace each `todo!()` in `src/` while preserving signatures. The public suite is declared as a Cargo test target, so run:

```text
cargo test --manifest-path starter/Cargo.toml
```

Implement modules in pipeline order: `url`, `http`, `html`, `css`, `style`, `layout`, `paint`, then `engine`. The crate intentionally uses no external dependencies.
