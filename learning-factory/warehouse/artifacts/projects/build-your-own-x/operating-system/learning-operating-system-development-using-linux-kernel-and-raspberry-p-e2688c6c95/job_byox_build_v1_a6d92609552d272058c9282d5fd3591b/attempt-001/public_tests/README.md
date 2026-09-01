# Public tests

`test_public.c` is a small contract sampler. It covers initialization, lifecycle scheduling, a cross-page memory round trip, copy-on-write isolation, and basic filesystem persistence. Each test starts from a fresh kernel object.

Run it through the starter build:

```sh
make -C starter public
```

The initial scaffold compiles and is expected to fail behavioral cases. Do not infer that untested edge cases are optional; capacity rollback, invalid input, corruption detection, and exhaustive lifecycle edges are independently checked.
