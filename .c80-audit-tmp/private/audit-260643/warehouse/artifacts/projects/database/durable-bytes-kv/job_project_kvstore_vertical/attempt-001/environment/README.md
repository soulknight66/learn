# Reproducible environment

Requires CPython 3.11+ on a POSIX-like system and no third-party packages. Validators set
`PYTHONDONTWRITEBYTECODE=1`, use temporary directories, and make no network requests.

Useful commands are listed in the root README. Set `KVSTORE_IMPL` to `reference` or
`production` for adversarial scripts. Benchmark JSON captures Python/platform metadata,
command parameters, raw per-operation timings, and summaries.
