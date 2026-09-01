# Working agreement for challenge agents

Work only on the Mica challenge in this repository.

## Goal

Complete the Pascal scaffold so that it implements the normative language in
`REQUIREMENTS.md` and passes the behavior-based public tests. Preserve a clean
separation between lexing, compiling, and execution.

## Constraints

- Do not read or reveal anything under `sealed/`.
- Do not add answers or reference code to `starter/`, `public_tests/`, or
  `environment/`.
- Keep source programs as read-only inputs; write build products only beneath
  `starter/bin/` or another explicit scratch directory.
- Invoke subprocesses through `environment/harness.py`, which uses argument
  arrays, a new process group, a wall deadline, descendant cleanup, and bounded
  captured output.
- Treat diagnostics, exit codes, and resource limits in `REQUIREMENTS.md` as part
  of the public interface.
- Add deterministic tests for each language feature or bug fix.
- Never claim a build or test passed unless the command actually ran.

## Useful commands

```bash
cd starter && make
MICA_BIN="$PWD/starter/bin/mica" python3 public_tests/run_tests.py
python3 -B -m unittest environment.test_harness -v
environment/check.sh
```

Free Pascal 3.2.x in Object Pascal mode is the intended toolchain. Avoid
implementation-defined behavior: use `Int64`, explicit bounds checks, and exact
instruction limits.
