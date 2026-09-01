# Reproducible environment

Requires CPython 3.11+ on a POSIX-like system and no third-party packages. Validators set
`PYTHONDONTWRITEBYTECODE=1`, use temporary directories, and make no network requests.

Exact individual commands and the `python3 scripts/run_all.py` entry point are listed in the
root README. Adversarial scripts resolve `KVSTORE_IMPL=reference` or
`KVSTORE_IMPL=production` themselves; no `PYTHONPATH` is required for those scripts. The
debugging regression additionally accepts `KVSTORE_IMPL=buggy`. Benchmark JSON captures
Python/platform metadata, command parameters, per-operation aggregate timings, and summaries.
