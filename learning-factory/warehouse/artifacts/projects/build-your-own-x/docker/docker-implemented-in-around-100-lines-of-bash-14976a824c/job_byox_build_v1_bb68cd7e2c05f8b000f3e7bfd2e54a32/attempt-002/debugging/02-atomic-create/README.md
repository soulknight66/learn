# Exercise 2: atomic create

`broken.sh` checks whether a state directory exists and later creates it. The
debug gate makes two creators reach the vulnerable interval at the same time.

Run:

```bash
bash debugging/02-atomic-create/test.sh
```

Exactly one concurrent creator must succeed. The loser must return nonzero,
and it must not overwrite or remove the winner's state. Preserve the debug
gate: it is part of the deterministic reproducer, not the proposed locking
mechanism.

