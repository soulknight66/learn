# Validation record

This file is completed from commands actually run in the allocated build workspace. The artifact
status intentionally remains `GENERATED` + `PARTIAL`; independent validators control stronger
labels.

Host context observed before generation:

- `gcc`/`cc`: GCC 8.5.0
- `ld`: GNU ld 2.30
- `make`: GNU Make 4.2.1
- `python3`: 3.6.8
- A probe compiling and linking `int main(void){return 0;}` with `cc -m32` exited 0.
- A freestanding 32-bit object probe exited 0.
- `qemu-system-i386`, `grub-mkrescue`, and `xorriso` were not found on `PATH`.

Exact post-generation commands and observed results are appended after implementation validation.
No boot, fuzz, benchmark, transfer, review, or production-readiness result is claimed.

## Commands and observed results

Commands below were run from the repository root unless `make -C` names another directory.

| Command | Exit | Observed result |
| --- | ---: | --- |
| `make -C starter host-check` | 0 | Strict C11 freestanding syntax check completed with no diagnostic. |
| `make -C sealed/reference host-check` | 0 | Strict C11 freestanding syntax check completed with no diagnostic. |
| `make -C public_tests SOURCE_DIR=../sealed/reference test` | 0 | `public tests: PASS (all)` |
| `make -C sealed/reference_tests test` | 0 | `reference tests: PASS` |
| `make -C sealed/production test` | 0 | `production audit prototype: PASS` (this is a prototype test, not a productionization claim). |
| `cc -std=c11 -Wall -Wextra -Werror -pedantic -fsyntax-only sealed/alternatives/bitmap_frames.c` | 0 | No compiler diagnostic. |
| `make -C starter kernel` | 0 | Linked `starter/build/tinykernel.elf` with `ld -m elf_i386`. |
| `make -C sealed/reference kernel` | 0 | Linked `sealed/reference/build/tinykernel.elf` with `ld -m elf_i386`. |
| `python3 environment/check_elf.py starter/build/tinykernel.elf` | 0 | `ELF check: PASS (ELF32, EM_386, entry=0x00101000, Multiboot v1)` |
| `python3 environment/check_elf.py sealed/reference/build/tinykernel.elf` | 0 | `ELF check: PASS (ELF32, EM_386, entry=0x00101000, Multiboot v1)` |
| `make -C benchmarks SOURCE_DIR=../sealed/reference build && ./benchmarks/build/bench_core` | 0 | Raw single sample: `frame cycles: 100000; clock ticks: 381` and `filesystem cycles: 100000; clock ticks: 12101`. |
| `make -C public_tests SOURCE_DIR=../starter test` | 2 | Expected incomplete-challenge result: `public tests: 27 failure(s)`; all four starter stages contain TODOs. |

## Informative failed attempts

The first run of `python3 environment/check_elf.py starter/build/tinykernel.elf` exited 1 with
`ELF check: FAIL: Multiboot v1 magic is absent from first 8192 bytes`. Inspection localized the
problem to a non-allocatable `.multiboot` assembly section. After adding the ELF allocatable section
flag, both images were rebuilt and produced the passing results above.

`make -C sealed/reference_tests sanitize` exited 2 during linking. The exact linker blockers were:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

Thus sanitizer execution was unavailable; no `FUZZED` or sanitizer-clean claim is made.

Scratch binaries linked from sealed sources in `public_tests/build/` and `benchmarks/build/` were
removed with their scoped `make clean` targets after validation so solution code is not exposed as
a learner-side binary.

The two timing values above are one unrepeated `clock()` sample on the shared generation host. They
are preserved as observed output, not generalized as throughput, a regression threshold, or a
`BENCHMARKED` label.

## Final policy checks

A final scoped repository scan exited 0 and reported:

```text
required_path_check=0
forbidden_path_check=0
regular_type_check=0
learner_answer_path_check=0
credential_pattern_scan=0
json_contract_check=0
```

The JSON contract check parsed both metadata files, compared `MANIFEST.yaml` with the authoritative
object, and cross-checked the immutable provenance identifiers. The credential scan covered all
generated text trees with patterns for common private-key headers, cloud/API token formats, and
credential assignments. A zero result means no matching generated path or pattern was found; it is
not a general security audit.

Final retained labels: `GENERATED`, `PARTIAL`. Independent validation remains required.
