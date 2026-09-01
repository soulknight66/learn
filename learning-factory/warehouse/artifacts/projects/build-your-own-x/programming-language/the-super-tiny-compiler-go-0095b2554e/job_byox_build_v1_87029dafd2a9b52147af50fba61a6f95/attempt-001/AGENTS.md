# Learner agent guide

Work only in `starter/` and use `public_tests/` as the visible acceptance suite. Read `REQUIREMENTS.md` before changing the public API.

- Keep the project dependency-free and compatible with Go 1.21 or newer.
- Preserve exported names, enum values, field meanings, and error contracts from the starter.
- Use deterministic traversal and slot allocation; do not rely on map iteration order.
- Do not bypass stages by evaluating source text directly in `Execute`.
- Do not add global mutable compiler or VM state.
- Do not weaken, delete, or special-case tests.
- Never inspect or copy material from `sealed/`; it belongs to independent validation.
- Do not add credentials, network access, generated binaries, symlinks, or vendored dependencies.

Before handing off, run `gofmt` on Go files and, when the toolchain is present, run both:

```bash
(cd starter && go test ./...)
(cd public_tests && go test ./...)
```

Report actual results. A prose claim or successful process exit is not evidence that independent validation passed.
