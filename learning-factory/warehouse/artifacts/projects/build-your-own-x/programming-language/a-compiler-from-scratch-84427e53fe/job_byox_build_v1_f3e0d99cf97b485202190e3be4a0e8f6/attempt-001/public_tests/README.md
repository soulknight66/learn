# Public tests

Run from the repository root:

```sh
ruby -Istarter/lib public_tests/test_public.rb
```

These tests reveal basic contracts for each stage and a few end-to-end cases. They intentionally omit many malformed inputs, scoping edges, arithmetic boundaries, bytecode validation cases, and CLI checks. Passing them does not imply completion.
