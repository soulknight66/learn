# Independent validation log

Review date: 2026-08-31. Commands ran from `CANDIDATE/` unless noted. In the command excerpts, `REVIEW_TMP="$PWD/../.review-tmp"` and `PY311=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`. All commands were bounded with `timeout` where execution could block. Because `/tmp`, `/var/tmp`, and immutable `CANDIDATE/` were unavailable to `tempfile`, reruns used the temporary reviewer-owned `REVIEW_TMP`; it was removed afterward.

## Integrity and environment

```bash
find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
find . -type f | wc -l
find . -type l | wc -l
```

Observed before and after tests: aggregate digest `ea836876cf3c9ea700832234b4dddf7d1ebf85a81489948ed2bdea6452154a8e`, 64 regular files, 0 symlinks. No candidate file changed.

```bash
python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
command -v python3.11
```

Observed: `Python 3.6.8`; `Python 3.11.5`; no `python3.11` path/output.

```bash
sha256sum MANIFEST.yaml PROVENANCE.json
```

Observed:

```text
14e7284f1cd12ae3500d7d115bcef8b0c4745132b5db72a30bab47a3ab99c7e5  MANIFEST.yaml
1f3aea35888029a1fe958dd6487b659ebc60040e401061c54c191e2a2368100f  PROVENANCE.json
```

An independent `ast.parse` walk parsed all 32 Python files. A source scan found no `.extract(`, `extractall(`, or `shell=True` call site; its only `shell=True` text match was the validator's diagnostic message.

## Learner command and reference suites

```bash
timeout 15s env TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

Observed: exit 1; 5 loader errors under Python 3.6.8, all reporting `SyntaxError: future feature annotations is not defined`. No test body ran.

```bash
timeout 30s env TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed: exit 0; `Ran 18 tests in 0.437s`; `OK`.

```bash
timeout 30s env TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed: exit 0; `Ran 22 tests in 1.257s`; `OK`.

```bash
timeout 30s env TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s adversarial -v
```

Observed: exit 0; `Ran 4 tests in 0.077s`; `OK`.

These are independently observed executions of submitted tests, not independent proof that their coverage is complete.

```bash
timeout 15s env TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest public_tests.test_models.IdentifierTests.test_accepts_boundary_and_punctuation
```

Observed: exit 1; 1 test, 1 error; intentional `NotImplementedError: milestone 1: validate identifiers`.

## Submitted structural and host checks

```bash
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/validate_pack.py
```

Observed: exit 0. Reported exact manifest, valid provenance JSON, 32 parsed Python files, 23 required paths, regular files only, 0 symlinks, 0 forbidden paths, 0 answer leaks, 0 credential hits, and 0 policy violations. Manual inventory separately confirmed that the three `ANSWER.md` files are all below `sealed/`.

```bash
timeout 15s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/probe_namespaces.py
```

Observed: exit 0:

```json
{"linux": true, "machine": "x86_64", "python": "3.11.5", "returncode": 0, "stderr": "", "supported": true, "unshare": "/usr/bin/unshare"}
```

This probes only `unshare --user --map-root-user -- true`; it does not establish full container isolation.

```bash
timeout 15s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m minibox --help
```

Observed: exit 0; help listed `image-import`, `create`, `inspect`, `events`, and `run`.

## Independent edge probes

A reviewer-authored temporary Python probe outside `CANDIDATE/` was run with Python 3.11.5 and `PYTHONPATH=CANDIDATE/sealed/reference`, then deleted. It performed four focused cases:

1. Passed a set and generator as `ContainerSpec.argv`: both were accepted.
2. Constructed `Runner` with NaN and infinity: both were accepted.
3. Used a custom backend returning `(sys.executable, "bad\0argument")`: `run()` raised raw `ValueError`; durable state was `RUNNING`, with events `["CREATED", "RUNNING"]`.
4. Replaced a layer immediately after `apply_layer` returned and before `_sha256` reopened it: extracted content was `applied-A`, while the manifest digest matched replacement B and not applied A.

The combined probe exited 0 and printed those observations as JSON.

CLI parsing independently confirmed the non-finite values:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'from minibox.cli import build_parser; print(build_parser().parse_args(["run","demo","--timeout","nan"]).timeout, build_parser().parse_args(["run","demo","--timeout","inf"]).timeout)'
```

Observed: exit 0; `nan inf`.

Set ordering was checked in three fresh interpreters:

```bash
env PYTHONHASHSEED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference "$PY311" -c \
  'from minibox.models import ContainerSpec; print(ContainerSpec("demo","base",{"alpha","beta","gamma","delta"}).argv)'
```

The same command was repeated with seeds 2 and 3. Observed orders differed:

```text
seed 1: ('beta', 'delta', 'gamma', 'alpha')
seed 2: ('delta', 'gamma', 'alpha', 'beta')
seed 3: ('gamma', 'beta', 'delta', 'alpha')
```

## Limitations

- Initial tempfile-dependent runs without `TMPDIR` were inconclusive environmental failures; all relevant suites were rerun with writable reviewer scratch.
- `git` and `rg` were unavailable. POSIX `find`, `grep`, hashes, AST parsing, and direct file inspection were used instead.
- Network access and the linked/source repositories were unavailable, so originality and linked-resource license claims could not be independently compared.
- No populated rootfs was supplied; full namespace execution was not attempted.
- No fuzz, benchmark, transfer, production, crash-recovery, or hostile concurrent-rootfs validation was performed. These remain unawarded/inconclusive, consistent with the submitted `GENERATED` + `PARTIAL` status.
