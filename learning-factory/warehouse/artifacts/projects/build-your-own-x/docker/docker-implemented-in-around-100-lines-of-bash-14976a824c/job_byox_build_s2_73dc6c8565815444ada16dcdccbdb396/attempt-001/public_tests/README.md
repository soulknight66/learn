# Public tests

`test_contract.sh` exercises visible controller behavior with a fake runner. It needs no root access
and never executes a command from a rootfs.

```bash
bash public_tests/test_contract.sh starter/tinybox.sh
```

You may pass another controller path as the first argument. The suite checks help, traversal-shaped
names, copy independence, deterministic listing, inspection, duplicate rejection, argv preservation,
exit-state recording, and deletion.

`fake_runner.sh` is a test double, not an isolation implementation. It records each received argv
element on a separate indexed line, prints a marker, and returns `TINYBOX_FAKE_EXIT` (zero by
default). Passing these tests therefore makes no claim about Linux namespace behavior.
