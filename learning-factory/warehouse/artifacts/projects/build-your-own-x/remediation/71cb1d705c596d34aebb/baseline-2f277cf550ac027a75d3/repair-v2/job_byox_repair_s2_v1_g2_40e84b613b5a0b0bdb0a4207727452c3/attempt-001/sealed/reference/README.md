# Sealed reference implementation

This directory contains an independently written reference used only for
instructor-side validation. It implements the learner-visible contract in one
C translation unit so ownership and cleanup paths can be audited together.

```sh
make -C sealed/reference \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

`make -C sealed/reference check` uses the pinned Python 3.11.5 runner by
default. `PYTHON` may select another Python 3.9-or-newer executable.

This is a reference for the scoped exercise, not a production shell. Known
hardening gaps are recorded in `sealed/production/PRODUCTIONIZATION.md` and
`sealed/REVIEW.md`.
