# Pocket Browser Engine

Build a small, deterministic browser pipeline in Rust: parse an `http://` URL, frame an HTTP/1.1 request and response, parse a deliberately small HTML/CSS language, apply the cascade, lay out boxes, and paint them into an in-memory RGB canvas.

This is not a standards-compliant or production-safe browser. Its purpose is to make trust boundaries and stage invariants visible. No third-party crates are needed.

## What you receive

- `REQUIREMENTS.md` is the normative behavior contract.
- `CONCEPTS.md` explains the systems ideas without giving implementation code.
- `DESIGN_QUESTIONS.md` contains questions to answer before coding.
- `starter/` is an API skeleton designed to compile with `todo!()` bodies.
- `public_tests/` is the visible conformance suite wired into the starter crate.
- `environment/` documents the expected offline toolchain.

Additional debugging, review, adversarial, and benchmark prompts can be revealed separately. Reference code and answer material are sealed and are not part of the learner view.

## Start here

From the repository root, with stable Rust installed:

```text
cargo test --manifest-path starter/Cargo.toml
```

Work in this order:

1. URL parsing and safe request construction.
2. Bounded HTTP response parsing.
3. HTML and CSS parsers with explicit limits.
4. Selector matching and the cascade.
5. Block-flow layout, text wrapping, and painting.
6. The injectable transport and end-to-end engine.

The visible tests are examples, not the entire specification. Handle malformed and oversized input without panics. Keep networking injectable so tests never depend on the public internet.

## Completion boundary

A good submission passes its tests, uses no `unsafe`, does not add network-fetched dependencies, and explains its security limits. Passing visible tests alone is not evidence of full correctness. Independent validation remains required.
