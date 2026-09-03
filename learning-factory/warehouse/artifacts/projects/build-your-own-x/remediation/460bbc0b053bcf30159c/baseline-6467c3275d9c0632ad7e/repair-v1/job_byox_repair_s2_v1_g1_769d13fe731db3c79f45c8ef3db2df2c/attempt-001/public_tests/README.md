# Public tests

These tests show the API's testing style and cover one ordinary path through each subsystem. They are
not exhaustive and do not replace `REQUIREMENTS.md`.

```sh
make -C public_tests run
```

The default build uses `../starter/src/cairn.c`. You can point the suite at another compatible source
and include directory with command-line `IMPL=... INCLUDE=...` values. Do not edit the suite to make a
broken implementation pass.
