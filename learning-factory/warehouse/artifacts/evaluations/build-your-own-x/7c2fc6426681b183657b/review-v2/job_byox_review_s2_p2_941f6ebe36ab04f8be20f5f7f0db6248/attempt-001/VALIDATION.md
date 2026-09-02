# Independent validation evidence

## Scope and result

Review date: 2026-09-02 (America/Chicago). Commands ran from the review workspace root. `CANDIDATE/`
was treated as immutable; all generated objects and executables went to a temporary reviewer
directory. Overall result: `REVISE` for reproducibility and audit-evidence defects, despite passing
behavioral evidence.

The shell launcher prepended account-mapping warnings from `/usr/bin/id` to commands. Those warnings
were ambient and were not emitted by candidate programs.

## Toolchains

Commands:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/as --version | sed -n '1p'
/usr/bin/ld --version | sed -n '1p'
/usr/bin/uname -s -m
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-as --version
```

Observed:

```text
Python 3.11.5
GNU assembler version 2.30-123.el8
GNU ld version 2.30-123.el8
Linux x86_64
openjdk version "21.0.5" 2024-10-15 LTS
GNU assembler (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203
```

Pinned Python was used for all Python-driven checks. System x86-64 binutils were useful and invoked
by absolute path; there was no configured pinned x86-64 binutils root. Java and Arm binutils were
available but not applicable to this x86-64 assembly artifact.

The configured QEMU initially lacked its matching GLib in the runtime search path:

```text
/arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 --version
```

Observed status 127 and:

```text
symbol lookup error: .../qemu-x86_64: undefined symbol: g_date_time_format_iso8601
```

With the configured library root:

```text
env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 --version
printf ': square dup * ; 12 square .\n' | \
  env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 \
  .review-run.UCyXrQ/cinder-reference-direct
```

Observed `qemu-x86_64 version 9.1.1`, status 0, and stdout `144\n`. This one smoke case is not a
`TRANSFER_VERIFIED` claim.

## Inventory, parsing, hashes, and candidate audit

Commands:

```text
find CANDIDATE -type l -print
find CANDIDATE -type f -printf '%P\n' | LC_ALL=C sort
(cd CANDIDATE && PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py)
/usr/bin/sha256sum CANDIDATE/MANIFEST.yaml CANDIDATE/PROVENANCE.json \
  CANDIDATE/sealed/reference/forth.S CANDIDATE/public_tests/test_cinder.py \
  CANDIDATE/sealed/reference_tests/test_reference.py CANDIDATE/environment/build.py \
  CANDIDATE/environment/audit.py
```

Observed 36 regular files and no symlinks. The audit returned status 0:

```json
{"credential_patterns": 4, "files_scanned": 36, "forbidden_absent": 21, "manifest_exact": true, "provenance_binding": true, "required_regular": 23, "special_entries_absent": true}
```

Observed hashes, all equal to the builder record:

```text
c22f0d3691104fb2f03556eb89753678280c3ee082ee91b6daa9ecd39e6c8858  CANDIDATE/MANIFEST.yaml
a07dc4005276491142d98b5a1b764a7aa11342f525027ef38be2a9d01565ed87  CANDIDATE/PROVENANCE.json
670afd00dc6b252e07498bf92d30250da931b255ac494cd1e3c81be363dca64e  CANDIDATE/sealed/reference/forth.S
a117ef205f04ff0c1f2202f04ec027ffefdf69ef3bc133c655d299e8c45f08cc  CANDIDATE/public_tests/test_cinder.py
ef7d2334dd89656c80e9453e5f6f7219bf9331404ad4df7b6e547d3b3a4e2eeb  CANDIDATE/sealed/reference_tests/test_reference.py
af783bedf227193b552b840a714d34c38cc7b7d4e3ffb60b940230210d4185f9  CANDIDATE/environment/build.py
504290279af3287f9047d12f7746958ab26b3a1330fb53d43bb54be1e37ebde1  CANDIDATE/environment/audit.py
```

An in-memory `compile()` pass accepted all five Python files, and `json.load()` accepted
`MANIFEST.yaml` and `PROVENANCE.json`. No bytecode was written.

## Builds and executable inspection

A scratch directory was created with `mktemp -d ./.review-run.XXXXXX`; this run yielded
`.review-run.UCyXrQ`.

Commands:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/build.py CANDIDATE/starter/forth.S \
  -o .review-run.UCyXrQ/cinder-starter
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/build.py CANDIDATE/sealed/reference/forth.S \
  -o .review-run.UCyXrQ/cinder-reference
/usr/bin/as --64 -o .review-run.UCyXrQ/reference-direct.o \
  CANDIDATE/sealed/reference/forth.S
/usr/bin/ld -m elf_x86_64 -z noexecstack \
  -o .review-run.UCyXrQ/cinder-reference-direct \
  .review-run.UCyXrQ/reference-direct.o
/usr/bin/file .review-run.UCyXrQ/cinder-starter \
  .review-run.UCyXrQ/cinder-reference-direct
/usr/bin/readelf -W -l .review-run.UCyXrQ/cinder-reference-direct
/usr/bin/readelf -W -s .review-run.UCyXrQ/cinder-reference-direct
```

All four assembler/linker operations returned 0. Both executables were static ELF64 x86-64 files.
The direct reference exported global `_start`; `GNU_STACK` was `RW`, not executable. An empty-input
bounded invocation of the starter returned 2, empty stdout, and exactly
`error: interpreter not implemented\n` on stderr. The reference smoke input returned 0, stdout
`144\n`, and empty stderr.

## Candidate-provided suites

Commands:

```text
CINDER_BIN=.review-run.UCyXrQ/cinder-reference PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s CANDIDATE/public_tests -v
REFERENCE_BIN=.review-run.UCyXrQ/cinder-reference PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s CANDIDATE/sealed/reference_tests -v
```

Observed:

```text
Ran 10 tests in 0.021s
OK
Ran 13 tests in 0.070s
OK
```

These reproduce builder-provided tests; they are not treated as independent proof by themselves.

## Independent black-box checks

The direct-build binary was exercised through an inline Python harness using argv-only subprocesses,
captured streams, and three-second timeouts. The command form was:

```text
REVIEW_REFERENCE=.review-run.UCyXrQ/cinder-reference-direct \
  PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
# run(payload) used subprocess.run([binary], input=payload,
#   stdout=PIPE, stderr=PIPE, timeout=3, check=False)
# Success assertions required (returncode, stdout, stderr) == (0, expected, b'').
# Error assertions required returncode == 2 and nonempty stderr.
# Seeded property source was generated with random.Random(34000401).
PY
```

The assertions covered empty input; every separator class including NUL; EOF comments; `#` inside a
word; non-ASCII byte names; output words; stack display; nested conditionals; recursion; stack,
input, patch, and dictionary exact/one-past boundaries; compile-only/reserved/duplicate/malformed
definitions; numeric endpoints; division traps; bounded nontermination; and 80 random signed-64-bit
tuples. Each tuple checked wrapping `+`, `-`, `*`, `and`, `or`, `xor`, `=`, `<`, `>`, `/`, and `mod`
against a Python oracle.

Observed:

```text
independent black-box assertions passed: 46
random arithmetic/bitwise/comparison/division tuples checked: 80
```

An initial draft incorrectly expected `256 zeroes depth` to succeed. It observed status 2 and
`error: data stack overflow\n`; that behavior is correct because `depth` itself pushes a 257th cell.
The corrected checks require 256 retained cells to succeed and `depth` at that point to fail. The
corrected harness then passed all 46 assertions.

## Reproducibility failure

Commands:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/build.py CANDIDATE/sealed/reference/forth.S \
  -o .review-run.UCyXrQ/repro-a
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/build.py CANDIDATE/sealed/reference/forth.S \
  -o .review-run.UCyXrQ/repro-b
/usr/bin/sha256sum .review-run.UCyXrQ/repro-a .review-run.UCyXrQ/repro-b
/usr/bin/cmp -s .review-run.UCyXrQ/repro-a .review-run.UCyXrQ/repro-b
/usr/bin/readelf -p .strtab .review-run.UCyXrQ/repro-a
/usr/bin/readelf -p .strtab .review-run.UCyXrQ/repro-b
```

Observed `cmp` status 1 and different hashes:

```text
168135573ab6c105edea98a0c8c2c0ef3ed1044baf944079634b56129c811896  repro-a
3b212d83269df78e2b9bc0e7fd693f1600f41dd4a5ac37c8c390386347906b1f  repro-b
```

The respective `.strtab` sections contained different random paths ending in
`cinder-build-1hxriww9/cinder.o` and `cinder-build-fgcmaodf/cinder.o`.

## Build-policy and audit-coverage adversarial checks

Commands (all links and outputs were inside reviewer scratch):

```text
/usr/bin/ln -s "$PWD/CANDIDATE/starter/forth.S" .review-run.UCyXrQ/source-link.S
/usr/bin/ln -s /usr/bin/as .review-run.UCyXrQ/as-link
/usr/bin/ln -s /usr/bin/ld .review-run.UCyXrQ/ld-link
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/build.py .review-run.UCyXrQ/source-link.S \
  -o .review-run.UCyXrQ/symlink-built \
  --assembler .review-run.UCyXrQ/as-link --linker .review-run.UCyXrQ/ld-link
```

Observed status 0 and a valid static ELF, demonstrating that resolution before `is_symlink()` makes
the documented guard ineffective.

Static inspection of `audit.py`'s literal `REQUIRED` tuple reported:

```text
core files omitted from audit REQUIRED: ['starter/forth.S', 'starter/Makefile',
'public_tests/test_cinder.py', 'environment/build.py', 'environment/audit.py',
'benchmarks/run.py']
```

Inspection of lines 110-117 also showed that `provenance_binding` checks only
`snapshot_sha256` and `project.project_id`, not the complete provenance object.

## Benchmark harness smoke only

Command:

```text
PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/benchmarks/run.py .review-run.UCyXrQ/cinder-reference-direct \
  --iterations 3 --terms 10 --timeout 3
```

Observed status 0 and JSON containing `iterations: 3`, `terms_per_process: 10`, provenance text, and
`validation_label: "UNVALIDATED_MEASUREMENT"`. Timing values were host-dependent and are not used as
benchmark evidence.

## Limitations

- The source catalog snapshot and linked upstream resource were unavailable in the review workspace;
  external provenance, license, and clean-room assertions are inconclusive.
- The sealed material is readable in this reviewer view. No student-view export was available to
  establish isolation, so no transfer label is justified.
- The public/sealed suites are builder-controlled. Independent checks were black-box and bounded,
  but not exhaustive or fuzzing.
- QEMU needed the separately configured GLib path. A single successful emulated smoke case does not
  establish platform transfer.

## Scratch cleanup

After recording the results, the scratch target was resolved and verified as the non-symlink
directory `.review-run.UCyXrQ`. Its seven generated files and three test symlinks were removed one
by one with `/usr/bin/unlink`, followed by `/usr/bin/rmdir ./.review-run.UCyXrQ`. The cleanup
returned 0. These disposable products are no longer directly recoverable, but every source and
command needed to regenerate them remains; no file under `CANDIDATE/` was removed or changed.
