# Public tests

The tests treat `msh` as a black box and use only Python's standard library plus ordinary POSIX utilities. They intentionally reveal behavior, not implementation structure.

Run all tests:

```sh
python3 public_tests/test_shell.py --shell starter/msh
```

Run a progressive group with the portable stage filter:

```sh
python3 public_tests/test_shell.py --shell starter/msh --stage parsing
python3 public_tests/test_shell.py --shell starter/msh --stage execution
python3 public_tests/test_shell.py --shell starter/msh --stage builtins
python3 public_tests/test_shell.py --shell starter/msh --stage jobs
```

The public suite does not prove descriptor hygiene, process-group correctness, terminal handoff, cleanup after injected failures, or freedom from zombies. Passing it is a milestone, not a production claim. Each test has a three-second timeout; a timeout commonly indicates that a pipe writer remains open or the parent waited before launching the full pipeline.
