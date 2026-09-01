# Working agreement

Implement only the learner-facing scaffold in `starter/`. Treat `sealed/` as evaluator-owned: do not
read it while solving and never copy material from it into learner-visible paths. The stable contract
is `REQUIREMENTS.md`; public tests are examples, not the complete specification.

Use only Python's standard library. Keep all execution deterministic, place no generated files outside
the repository, and do not execute untrusted Minnow bytecode without validation and a step limit.

Suggested loop:

```bash
PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m minnow exec public_tests/fixtures/countdown.mno
```

Do not weaken tests, change published opcode values, or rely on machine-specific integer behavior.
Add tests for each edge case you implement.
