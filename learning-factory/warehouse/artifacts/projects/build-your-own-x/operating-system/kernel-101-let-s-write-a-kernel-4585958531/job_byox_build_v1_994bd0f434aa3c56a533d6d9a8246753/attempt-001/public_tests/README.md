# Public tests

These tests compile the subsystem source directly and exercise only documented behavior. Each
stage target runs exactly one subsystem; `test` runs all four.

```sh
make stage1
make stage2
make stage3
make stage4
make test
```

The default `SOURCE_DIR` is `../starter`. Build output stays in `public_tests/build/`. Tests are
examples rather than an exhaustive validator: boundary ordering, state corruption resistance, and
freestanding ELF behavior may be checked independently.
