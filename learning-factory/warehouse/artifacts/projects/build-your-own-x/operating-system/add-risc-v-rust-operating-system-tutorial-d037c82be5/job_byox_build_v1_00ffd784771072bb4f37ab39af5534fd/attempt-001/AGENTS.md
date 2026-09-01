# Learner agent guide

Work only in `starter/`. Treat `REQUIREMENTS.md` as the contract and do not
weaken, delete, or special-case tests. `public_tests/` may be read and run but
must not contain implementation code.

Use stable Rust and the standard library only. Keep the crate free of `unsafe`,
platform-specific syscalls, nondeterministic iteration, ambient environment
state, and network dependencies. Return typed errors for expected invalid
input. Avoid panics except for an internal invariant that callers cannot
violate.

Recommended loop:

```bash
cargo fmt --manifest-path starter/Cargo.toml -- --check
cargo test --manifest-path public_tests/Cargo.toml
cargo clippy --manifest-path starter/Cargo.toml --all-targets -- -D warnings
```

Add your own tests for every state transition and for failure atomicity. In
particular, compare allocator and object state before and after rejected
operations. Do not inspect or depend on `sealed/`; it represents evaluator-only
material and is not part of the learner contract.
