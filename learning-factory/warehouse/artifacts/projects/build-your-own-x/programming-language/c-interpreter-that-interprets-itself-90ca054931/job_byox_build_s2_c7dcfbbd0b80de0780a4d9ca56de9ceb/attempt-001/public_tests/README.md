# Public conformance tests

Set `MICROC_BIN` to an Ember-C executable and run `./public_tests/run.sh` from
the repository root.  Tests launch the executable with argument arrays, bounded
timeouts, and captured output.

```sh
MICROC_BIN="$PWD/starter/build/emberc" public_tests/run.sh
```

During the lexer milestone, use `public_tests/run.sh --lexer-only`.  The full
suite covers representative behavior but deliberately omits many malformed
bytecode, resource-limit, deep-scope, and tower cases.
