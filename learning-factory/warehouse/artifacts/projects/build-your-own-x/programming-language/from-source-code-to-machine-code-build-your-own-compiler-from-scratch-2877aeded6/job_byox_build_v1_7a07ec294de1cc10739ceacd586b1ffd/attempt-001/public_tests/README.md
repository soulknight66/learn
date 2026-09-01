# Public tests

These tests demonstrate the contract without exhausting it. They cover tokenization, precedence,
scope behavior, binary shape, execution, validation-before-output, limits, and CLI smoke behavior.
Expect failures until the corresponding TODOs are implemented.

Run:

```bash
PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Hidden independent validation may vary whitespace and identifiers, exercise every opcode, mutate
lengths and jump targets, check 64-bit boundaries, and assert that malformed programs never emit
output. Passing only these examples is insufficient.
