# Starter guide

`tinybox.sh` already contains the command dispatcher and the public function boundaries. Its
stateful operations are TODOs. `runner.sh` contains the isolated-execution interface but does not yet
enter namespaces.

Recommended milestones:

1. Implement state initialization, name validation, and safe path construction.
2. Implement `create`, then `list` and `inspect`.
3. Add atomic per-name locks and status replacement.
4. Implement `delete` with a narrowly validated removal target.
5. Implement `run` against `public_tests/fake_runner.sh`.
6. Implement the real Linux runner last; it needs host kernel support that the other stages do not.

Run one visible suite repeatedly:

```bash
bash public_tests/test_contract.sh starter/tinybox.sh
```

The starter is expected to fail most cases until you implement it. A passing public suite is useful
feedback, not proof that path handling, races, signals, or isolation are correct.
