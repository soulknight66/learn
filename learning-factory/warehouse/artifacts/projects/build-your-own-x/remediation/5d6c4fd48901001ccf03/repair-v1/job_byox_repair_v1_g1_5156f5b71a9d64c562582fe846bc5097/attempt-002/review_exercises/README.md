# Code-review exercises

Review each deliberately unsafe fragment. For each, provide an exploit-shaped test case, explain the
trust-boundary violation, propose a fix that preserves argument boundaries, and name one residual risk
the fix does not solve.

## Shell injection

```python
def launch(rootfs, command):
    line = f"unshare --mount --pid --fork chroot {rootfs} {' '.join(command)}"
    return subprocess.run(line, shell=True, capture_output=True)
```

Consider adversarial values in both `rootfs` and individual command arguments. Review error handling
and timeout behavior as well as process construction.

## Rootfs escape

```python
def candidate(rootfs, command):
    path = os.path.abspath(os.path.join(rootfs, command.lstrip("/")))
    if not path.startswith(os.path.abspath(rootfs)):
        raise ValueError("outside root")
    return path
```

Consider neighboring path prefixes, traversal, symbolic links at every component, concurrent rootfs
changes, file type, and executability. State which guarantees belong in the educational resolver and
which require stronger kernel primitives.

Instructor answers are stored only in `sealed/review_exercises/`.

