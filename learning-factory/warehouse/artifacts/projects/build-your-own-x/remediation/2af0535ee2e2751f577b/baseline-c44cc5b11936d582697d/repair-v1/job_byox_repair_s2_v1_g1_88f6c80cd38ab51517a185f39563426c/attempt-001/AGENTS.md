# Learner agent contract

Work only in `starter/` unless a task explicitly asks you to write a design response elsewhere. Treat `sealed/` and harness-controlled exercise directories as unavailable evaluation material.

Preserve these properties:

- Use C11 and keep the supplied CLI and exit-code contract.
- Do not read or copy from `sealed/`.
- Do not hard-code public test inputs or expected output.
- Keep diagnostics on standard error and program output on standard output.
- Avoid signed-overflow undefined behavior; arithmetic failures are runtime errors.
- Keep fixed resource limits deterministic, or document and test a deliberate replacement.
- Invoke subprocesses, if added, with argument arrays and bounded timeouts rather than shell command strings.

Useful commands:

```sh
make -C starter clean all
python3 public_tests/run_tests.py --binary starter/build/sprig
starter/build/sprig --tokens starter/examples/hello.sprig
starter/build/sprig --disassemble starter/examples/hello.sprig
```

A prose claim of completion is not evidence. Leave the tree buildable and let the supplied tests and independent validators establish behavior.
