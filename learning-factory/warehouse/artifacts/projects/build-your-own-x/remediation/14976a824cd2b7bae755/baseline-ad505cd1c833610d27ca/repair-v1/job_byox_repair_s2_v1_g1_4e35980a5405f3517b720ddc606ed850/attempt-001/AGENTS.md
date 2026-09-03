# Learner and agent guide

Work only on the two scripts in `starter/` unless an exercise explicitly asks for a new learner test.
Treat `REQUIREMENTS.md` as normative and keep the CLI deterministic.

## Safety rules

- Never run a container command with `eval`, `source`, `bash -c`, or a reconstructed command string.
- Quote every path and forward commands as Bash arrays.
- Reject container names before constructing a path from them.
- Never recursively delete a caller-provided path. Deletion must target exactly a validated
  container directory beneath the configured state directory.
- Do not weaken the explicit `--` separator on `run`.
- Do not claim that namespaces are available merely because `unshare` is installed.
- Use temporary directories in tests and always set `TINYBOX_STATE_DIR`.

## Checks

From the repository root:

```bash
bash -n starter/tinybox.sh starter/runner.sh
bash public_tests/test_contract.sh starter/tinybox.sh
bash environment/check.sh
```

The visible suite is incomplete by design. Consider races, interrupted runs, malicious names,
symlinks, unusual arguments, and a runner that returns nonzero.
