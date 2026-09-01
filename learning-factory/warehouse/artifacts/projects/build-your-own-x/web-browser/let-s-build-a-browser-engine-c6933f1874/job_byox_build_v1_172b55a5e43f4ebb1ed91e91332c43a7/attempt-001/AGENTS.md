# Agent instructions

Work only in `starter/` unless the exercise explicitly reveals another learner-facing directory. Treat `REQUIREMENTS.md` as normative and public tests as examples.

- Use stable Rust and the standard library only.
- Do not fetch dependencies or contact real hosts while testing.
- Preserve the public API unless a requirement explicitly permits a change.
- Return structured `BrowserError` values for untrusted input; do not panic.
- Enforce limits before allocating or recursing.
- Keep HTTP bytes distinct from decoded document text.
- Run `cargo fmt --check` and `cargo test --manifest-path starter/Cargo.toml` when available.
- Do not inspect or copy sealed material. Document assumptions in your own submission.

Generated artifacts and prose claims are not validation. Record exact commands and observed results.
