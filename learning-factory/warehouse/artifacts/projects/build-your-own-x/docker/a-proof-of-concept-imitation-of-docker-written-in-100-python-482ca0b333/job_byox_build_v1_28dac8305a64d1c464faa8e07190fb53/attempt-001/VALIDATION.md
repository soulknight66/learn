# Validation record

All observations below were made in the allocated workspace on 2026-08-31. They are local build evidence only; the independent harness, not this file, assigns validation labels.

## Interpreter discovery and retained failed attempt

```bash
python3 --version
```

Observed: exit 0, `Python 3.6.8`.

```bash
PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -v
```

Observed: exit 1. The unittest loader reported 5 module import errors because Python 3.6 does not support `from __future__ import annotations`. No test body ran. This informative failure established the Python 3.11 dependency.

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed: exit 0, `Python 3.11.5`.

## Reference tests

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed: exit 0, `Ran 18 tests in 0.416s`, `OK`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```

Observed: exit 0, `Ran 22 tests in 1.272s`, `OK`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s adversarial -v
```

Observed: exit 0, `Ran 4 tests in 0.061s`, `OK`.

The runner tests used an explicit direct-process test backend. They tested argv preservation, a minimal environment, nonzero exit semantics, launch failure, timeout/process-group termination, and bounded retained output; they did not claim kernel namespace isolation.

## CLI and host capability

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m minibox --help
```

Observed: exit 0. Help listed `image-import`, `create`, `inspect`, `events`, and `run`.

```bash
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/probe_namespaces.py
```

Observed: exit 0.

```json
{"linux": true, "machine": "x86_64", "python": "3.11.5", "returncode": 0, "stderr": "", "supported": true, "unshare": "/usr/bin/unshare"}
```

This probe establishes only that a rootless user namespace can be created. A real MiniBox namespace payload was not run because the artifact intentionally includes no third-party root filesystem or executable image. Mount/PID/UTS/IPC setup, chroot contents, and workload isolation remain unverified.

## Starter sentinel

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest public_tests.test_models.IdentifierTests.test_accepts_boundary_and_punctuation
```

Observed: exit 1, `Ran 1 test in 0.004s`, `FAILED (errors=1)`. The error was the intentional `NotImplementedError: milestone 1: validate identifiers`, confirming the learner starter remains incomplete.

## Structure, boundary, and credential scan

```bash
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/validate_pack.py
```

Observed: exit 0.

```json
{"answer_files_outside_sealed": 0, "forbidden_present": 0, "high_confidence_credential_hits": 0, "manifest_exact": true, "policy_violations": 0, "provenance_json_valid": true, "provenance_raw_sha256": "1f3aea35888029a1fe958dd6487b659ebc60040e401061c54c191e2a2368100f", "python_files_parsed": 32, "regular_only": true, "required_files": 23, "symlinks": 0}
```

The raw provenance file hash above is a file-integrity observation, distinct from the immutable catalog snapshot identifier stored in the manifest.

## Explicitly unvalidated

No fuzzing campaign or benchmark harness was run, no full namespace container was launched, and no production readiness review approved deployment. Status remains **GENERATED + PARTIAL**, and independent validation remains **REQUIRED**.
