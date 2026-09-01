# Validation record

Date: 2026-08-31 (America/Chicago)

Artifact labels remain `GENERATED` and `PARTIAL`. Independent validation is required. The generation host has no Rust toolchain, so neither crate was compiled, formatted, or tested here.

## Tool availability

Command:

```text
python3 --version
```

Observed output, exit 0:

```text
Python 3.6.8
```

Command:

```text
rustc --version
```

Observed output, exit 127:

```text
/bin/bash: rustc: command not found
```

Command:

```text
cargo --version
```

Observed output, exit 127:

```text
/bin/bash: cargo: command not found
```

Command:

```text
rustfmt --version
```

Observed output, exit 127:

```text
/bin/bash: rustfmt: command not found
```

## Rust validation attempts

Each of these commands was attempted from the repository root:

```text
cargo fmt --manifest-path sealed/reference/Cargo.toml -- --check
cargo test --manifest-path sealed/reference/Cargo.toml
cargo test --manifest-path starter/Cargo.toml
```

Each produced the following output and exited 127:

```text
/bin/bash: cargo: command not found
```

These are informative failed attempts, not passing build or test evidence. Reference integration-test wrappers include both `public_tests/browser_engine_public.rs` and `sealed/reference_tests/conformance.rs`; their results are unknown until run by an independent Rust-equipped validator. The starter suite is expected to fail at unimplemented `todo!()` bodies and is the learner task.

## Structural audit

The deterministic audit command is:

```text
python3 environment/audit.py
```

Observed output, exit 0:

```text
PASS: 23 required files are regular files
PASS: 21 forbidden paths are absent
PASS: manifest and provenance match their authoritative JSON values
PASS: no symlinks, special files, or recognized credential material found
```

The audit excludes the orchestrator-owned `JOB.md` and `.factory-workspace` from credential-content scanning and does not modify them. It does verify their filesystem types along with the rest of the allocated tree. The scan covers all generated files.

The final static check was run as one shell invocation:

```text
python3 environment/audit.py
python3 -m json.tool MANIFEST.yaml >/dev/null
python3 -m json.tool PROVENANCE.json >/dev/null
if grep -R -n 'todo!' sealed public_tests; then exit 1; fi
if grep -R -n -E 'unsafe[[:space:]]*\{' starter public_tests sealed; then exit 1; fi
```

Observed output, exit 0:

```text
PASS: 23 required files are regular files
PASS: 21 forbidden paths are absent
PASS: manifest and provenance match their authoritative JSON values
PASS: no symlinks, special files, or recognized credential material found
```

The redirected JSON parsers and the two negative source scans produced no output. This proves structural and leakage checks only; it is not Rust compilation evidence.

## Unperformed validation

No build, passing Rust test, fuzz run, benchmark, profiler run, external network access, transfer verification, or production-readiness validation is claimed. An independent validator should install stable Rust, run the commands above, inspect any compiler diagnostics, and retain `PARTIAL` unless its own evidence justifies another label through the orchestrator.
