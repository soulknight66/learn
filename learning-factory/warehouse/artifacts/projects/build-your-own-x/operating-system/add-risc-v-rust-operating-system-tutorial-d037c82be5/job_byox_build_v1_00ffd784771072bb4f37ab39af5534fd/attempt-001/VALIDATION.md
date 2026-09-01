# Validation record

Generated in the allocated workspace on 2026-08-31 (America/Chicago). Commands
below were run from the repository root. Status remains `GENERATED + PARTIAL`;
independent validators decide all stronger labels.

## Host capability probe

Command (exit 0):

```bash
python3 --version
for tool in rustc cargo rustup rustfmt qemu-system-riscv64 qemu-system-riscv32; do
  if command -v "$tool" >/dev/null 2>&1; then
    command -v "$tool"
  else
    printf '%s: NOT FOUND\n' "$tool"
  fi
done
```

Observed output:

```text
Python 3.6.8
rustc: NOT FOUND
cargo: NOT FOUND
rustup: NOT FOUND
rustfmt: NOT FOUND
qemu-system-riscv64: NOT FOUND
qemu-system-riscv32: NOT FOUND
```

QEMU is not required for this host semantic model, but its absence also means
no emulator or boot claim can be made.

## Informative failed attempt

The first run of `python3 environment/check_structure.py` exited 1 because the
initial helper used a feature introduced after the installed Python:

```text
File "environment/check_structure.py", line 3
  from __future__ import annotations
  ^
SyntaxError: future feature annotations is not defined
```

The helper was changed to Python 3.6-compatible annotations. The corresponding
first `python3 environment/run_public.py` attempt failed for the same syntax
reason. No project code or validation result was inferred from those failures.

## Structural, provenance, and credential checks

Command (exit 0):

```bash
python3 environment/check_structure.py
```

Observed output:

```text
STRUCTURE_CHECK: PASS (23 required paths, 21 forbidden paths)
MANIFEST_CHECK: PASS (strict JSON and exact object)
PROVENANCE_CHECK: PASS (exact canonical object and immutable identity)
ENTRY_TYPE_CHECK: PASS (directories and regular files only)
CREDENTIAL_SHAPE_SCAN: PASS
```

The checker verifies every authoritative required path is a regular file, each
forbidden path is absent, all archive entries are regular files/directories,
the manifest is exactly the supplied JSON object, provenance matches its full
canonical-object digest and immutable identities, and generated text has none
of the private-key, AWS access-key, or assigned-secret shapes defined in the
checker. This is deterministic structural evidence, not independent semantic
validation.

An additional archive-type command exited 0 with empty output:

```bash
find . -type l -o -type b -o -type c -o -type p -o -type s
```

## Implementation and test inventory

This command exited 0:

```bash
find starter public_tests sealed/reference sealed/reference_tests -type f -name '*.rs' | sort
```

Observed output:

```text
public_tests/tests/filesystem.rs
public_tests/tests/memory.rs
public_tests/tests/process.rs
sealed/reference/src/fs.rs
sealed/reference/src/lib.rs
sealed/reference/src/memory.rs
sealed/reference/src/process.rs
sealed/reference_tests/tests/filesystem.rs
sealed/reference_tests/tests/memory.rs
sealed/reference_tests/tests/process.rs
starter/src/fs.rs
starter/src/lib.rs
starter/src/memory.rs
starter/src/process.rs
```

## Rust build and tests

Command (exit 2):

```bash
python3 environment/run_public.py
```

Observed output:

```text
PUBLIC_TESTS: BLOCKED (cargo not found on PATH)
```

Consequently, none of these were claimed or fabricated: Rust compilation,
public/reference test execution, formatting, Clippy, fuzzing, benchmarking,
QEMU boot, hardware transfer, review approval, or production readiness. A
machine with stable Rust must run at least:

```bash
cargo test --manifest-path public_tests/Cargo.toml
cargo test --manifest-path sealed/reference/Cargo.toml
cargo test --manifest-path sealed/reference_tests/Cargo.toml
```

The only artifact labels are the mandated `GENERATED` and `PARTIAL`, and
`independent_validation` remains `REQUIRED`.
