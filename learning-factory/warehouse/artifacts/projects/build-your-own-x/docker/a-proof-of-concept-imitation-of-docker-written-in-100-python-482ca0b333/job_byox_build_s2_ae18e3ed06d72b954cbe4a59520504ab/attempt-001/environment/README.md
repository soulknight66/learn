# Environment

The baseline targets CPython 3.11 on a POSIX host and uses only the standard library: `argparse`,
`dataclasses`, `enum`, `hashlib`, `json`, `os`, `pathlib`, `re`, `shutil`, `signal`, `sqlite3`,
`subprocess`, `tarfile`, `tempfile`, and `unittest`.

No package installation, network access, Docker daemon, root access, compiler, or external namespace
binary is required. The archived pack contains only regular files and directories. POSIX negative
tests briefly create symbolic links inside disposable temporary directories to verify rejection; no
link is retained as an artifact.

The reference validation used the exact interpreter recorded in `VALIDATION.md`. Learners may use a
compatible `python3`, but should record its absolute path and `python3 --version` when reporting
results. Real namespace isolation is intentionally not exercised: capabilities and policy vary by
host, and elevating this educational runtime would be unsafe.
