# Environment

The project requires a Go toolchain supporting Go 1.20 language features or
newer. It has no third-party modules, generators, services, environment
variables, or network setup.

Useful reproducible checks from the repository root are:

```bash
(cd starter && go test ./...)
(cd public_tests && go test ./...)
(cd sealed/reference && go test ./...)
(cd sealed/reference_tests && go test ./...)
```

The last two paths are instructor/validator material and are not part of the
learner view. Host details and actually observed results belong in
`VALIDATION.md`; do not infer support from this requirements note.
