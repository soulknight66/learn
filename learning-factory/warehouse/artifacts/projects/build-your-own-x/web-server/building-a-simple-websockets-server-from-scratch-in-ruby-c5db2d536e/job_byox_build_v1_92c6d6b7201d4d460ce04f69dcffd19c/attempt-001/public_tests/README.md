# Public tests

The public suite checks a representative slice of the required API: handshake
derivation and validation, canonical frame encoding, masking, incremental
decoding, limit rejection, and basic connection state. It deliberately omits
many adversarial sequences and concurrency races.

From `starter/`, run:

```bash
ruby -Ilib ../public_tests/run.rb
```

The runner uses no gems. It prints one line per check and exits 0 only when all
checks pass. To exercise a compatible implementation elsewhere, set
`TINY_WS_LIB` to the directory containing `tiny_ws.rb`.

Do not modify these tests merely to make failures disappear. Passing them does
not replace the requirements or independent validation.

