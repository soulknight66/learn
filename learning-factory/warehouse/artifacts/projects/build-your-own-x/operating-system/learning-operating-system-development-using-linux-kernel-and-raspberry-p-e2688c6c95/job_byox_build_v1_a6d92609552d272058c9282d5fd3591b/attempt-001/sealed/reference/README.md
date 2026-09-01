# Sealed reference implementation

This directory contains the independently generated reference implementation for the portable PebbleOS model. It is evaluation material and must not be included in the learner view.

The implementation uses fixed arrays, validates complete memory transfers before copying, reserves copy-on-write frames before mutation, derives filesystem open counts from descriptors, and supplies a non-mutating invariant checker. It is a semantic reference for this challenge, not a production kernel.

Host build:

```sh
make -C sealed/reference clean all
```

Reference tests are maintained separately under `sealed/reference_tests/`. The `pi3/` subdirectory records a small target adapter experiment; it is not validated on this host.
