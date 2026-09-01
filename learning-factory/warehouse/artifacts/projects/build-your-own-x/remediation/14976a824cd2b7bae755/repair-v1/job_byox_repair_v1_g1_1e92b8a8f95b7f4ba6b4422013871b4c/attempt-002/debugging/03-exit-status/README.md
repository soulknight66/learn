# Exercise 3: exit status and cleanup

`broken.sh` models the lifecycle around an isolation helper. It records
`RUNNING`, invokes a child, and restores `CREATED`. The child output is fine,
but callers never see a nonzero child status.

Run:

```bash
bash debugging/03-exit-status/test.sh
```

Repair the wrapper so it always attempts the state restoration after an
ordinary child exit and returns the child's exact status. A state-write
failure must not be silently ignored; document which failure wins if both the
child and cleanup fail. Signal handling is outside this small reproducer but
should be considered in the main runtime.

