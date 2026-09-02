# Environment

The baseline targets CPython 3.11 on a POSIX host and uses only the standard library: `argparse`,
`dataclasses`, `enum`, `fcntl`, `hashlib`, `json`, `os`, `pathlib`, `re`, `shutil`, `signal`,
`sqlite3`, `subprocess`, `tarfile`, `tempfile`, and `unittest`. `fcntl.flock` supplies POSIX
per-content image-publication locks; Windows is not a supported target.

No package installation, network access, Docker daemon, root access, compiler, or external namespace
binary is required. The archived pack contains only regular files and directories. POSIX negative
tests briefly create symbolic links inside disposable temporary directories to verify rejection; no
link is retained as an artifact.

`ProcessRunner` puts its unlinked file-backed captures in the validated child `cwd` by default, so
that directory must be writable for temporary-file creation. Callers that cannot provide a writable
`cwd` may pass an existing real writable `scratch_dir` to the constructor. CLI evaluator subprocesses
use an explicit writable working directory; no implicit system temporary directory is required by the
inner runner.

## Student-view release control

`student_view_allowlist.json` is a sorted, exact-file allowlist. Check the source pack without
creating an output tree:

```bash
python3 environment/export_student_view.py --source . --check
```

An authorized distributor can replace `--check` with `--destination /new/path`. The destination and
its parent must be separate from this production pack, and the destination must not exist. The
exporter rejects links and non-regular allowlisted entries, copies no unlisted path, and atomically
names the completed directory. In particular, it excludes `sealed/`, private tests, answers,
instructor exercises, provenance review records, and `VALIDATION.md`. It includes
`COPYING_NOTICE.md`; that learner-safe source boundary and generated-material grant must remain with
every copy of the exported learner view.

The reference validation used the exact interpreter recorded in `VALIDATION.md`. Learners may use a
compatible `python3`, but should record its absolute path and `python3 --version` when reporting
results. Real namespace isolation is intentionally not exercised: capabilities and policy vary by
host, and elevating this educational runtime would be unsafe.
