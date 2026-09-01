# Independent validation record

Date: 2026-08-31. Commands were run from the review workspace. Because `CANDIDATE/` is immutable,
all commands that create build products ran against a writable `cp -a` scratch copy; the original
was inspected only. Every potentially long-running command was bounded with `timeout` (45 seconds
for compilation/tests and 15 seconds per micro-workload execution).

## Environment

| Item | Observed |
| --- | --- |
| `cc` / `gcc` | GCC 8.5.0 |
| `ld` | GNU ld 2.30 |
| `make` | GNU Make 4.2.1 |
| `python3` | Python 3.6.8 |
| ELF inspection | `readelf`, `objdump`, and `nm` available |
| Not found on `PATH` | `qemu-system-i386`, `grub-file`, `grub-mkrescue`, `xorriso`, `clang`, `valgrind`, `cppcheck`, `scan-build`, `git` |

Scratch setup (the random directory suffix was `.review-scratch.SAttOT` in this run):

```sh
REVIEW_COPY=$(mktemp -d -p "$PWD" .review-scratch.XXXXXX)
cp -a CANDIDATE "$REVIEW_COPY/CANDIDATE"
chmod -R u+w "$REVIEW_COPY/CANDIDATE"
cd "$REVIEW_COPY/CANDIDATE"
```

## Commands and observed results

| Command | Exit | Observed result |
| --- | ---: | --- |
| `make -C starter host-check` | 0 | Strict C11 syntax/freestanding check emitted no diagnostic. |
| `make -C sealed/reference host-check` | 0 | Strict C11 syntax/freestanding check emitted no diagnostic. |
| `make -C public_tests SOURCE_DIR=../sealed/reference test` | 0 | `public tests: PASS (all)` |
| `make -C sealed/reference_tests test` | 0 | `reference tests: PASS` |
| `make -C sealed/reference_tests CFLAGS='-O2 -std=c11 -Wall -Wextra -Werror -pedantic -I../reference/include' test` after clean | 0 | `reference tests: PASS` at `-O2`. |
| `make -C sealed/production test` | 0 | `production audit prototype: PASS`; this is not productionization evidence. |
| `cc -std=c11 -Wall -Wextra -Werror -pedantic -fsyntax-only sealed/alternatives/bitmap_frames.c` | 0 | No diagnostic. |
| `make -C public_tests SOURCE_DIR=../starter test` | 2 | Reproduced `public tests: 27 failure(s)` for the intentionally incomplete starter. |
| `make -C sealed/reference_tests sanitize` | 2 | Link failed: `/usr/lib64/libasan.so.5.0.0` and `/usr/lib64/libubsan.so.1.0.0` not found. No sanitizer execution occurred. |
| `make -C starter kernel` | 0 | Produced `starter/build/tinykernel.elf`. |
| `make -C sealed/reference kernel` | 0 | Produced `sealed/reference/build/tinykernel.elf`. |
| `python3 environment/check_elf.py starter/build/tinykernel.elf` | 0 | Reported ELF32, EM_386, entry `0x00101000`, and Multiboot magic. |
| `python3 environment/check_elf.py sealed/reference/build/tinykernel.elf` | 0 | Reported ELF32, EM_386, entry `0x00101000`, and Multiboot magic. |
| `nm -u starter/build/tinykernel.elf` and the same reference command | 0 | Both produced empty output: no undefined symbols. |
| `objdump -s -j .multiboot starter/build/tinykernel.elf` | 0 | Bytes were `02b0ad1b 03000000 fb4f52e4`; interpreted little-endian, magic + flags + checksum wraps to zero. |
| `make -C benchmarks SOURCE_DIR=../sealed/reference build` | 0 | Built with GCC `-O2`. |
| Five runs of `./benchmarks/build/bench_core` | 0 each | Every run completed 100000 frame and 100000 filesystem cycles. Frame ticks: 411, 595, 552, 375, 418. Filesystem ticks: 13647, 12194, 13187, 12333, 12067. |

Independent `readelf -W -h/-l/-S` observations for the starter image:

- ELF32 little-endian Intel 80386 executable; entry `0x00101000`.
- `.multiboot` is allocatable at file offset `0x1000`, inside the first executable `PT_LOAD`.
- The entry lies in that executable segment.
- The BSS `PT_LOAD` has `p_vaddr=0x00103000` and `p_paddr=0x0010549c`.
- The reference BSS segment similarly has `p_vaddr=0x00104000` and
  `p_paddr=0x00106304`.

The last observation is not declared a boot failure: QEMU/GRUB were unavailable. It is recorded
because the supplied checker does not assess physical load layout.

## Reviewer-authored contract probes

A temporary harness outside `CANDIDATE/` was compiled directly with the four reference sources:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -ICANDIDATE/sealed/reference/include reviewer_harness.c \
  CANDIDATE/sealed/reference/src/frames.c \
  CANDIDATE/sealed/reference/src/scheduler.c \
  CANDIDATE/sealed/reference/src/vm.c \
  CANDIDATE/sealed/reference/src/ramfs.c -o reviewer_harness
./reviewer_harness
```

The same command was repeated with `-O2`. Both executions exited 0 and printed:

```text
vm reinit probe: mappings_before=1 free_before=1 mappings_after=0 free_after=1
reviewer edge checks: 178 checks, 0 failures
```

The 178 checks covered full frame exhaustion/reuse, unchanged state on failures, scheduler
block/wake/exit/cursor sequences, PID exhaustion, combined VM permission requirements, address
`0xffffffff`, duplicate-map atomicity, maximum filesystem names/data, complete sentinel comparison
after a short read, null/zero-length behavior, and state snapshots after rejected operations. The
VM reinitialization values were reported as a lifecycle finding rather than counted as a failure,
because the public contract does not state whether repeat initialization is supported.

## Metadata, boundary, and integrity checks

Python JSON parsing (the manifest is JSON-compatible YAML) confirmed all of the following as true:

```text
schema_version
project_id
source_id
source_commit
snapshot_binding (MANIFEST.provenance_sha256 == PROVENANCE.snapshot_sha256)
productionized == false
validation_labels == [GENERATED, PARTIAL]
linked_resource_license == NOASSERTION
```

Literal file digests were:

```text
MANIFEST.yaml   9c4bdeca7ef93a0a15376b0323fd2d64c31d403d23838aaeff7d61ada3aedddb
PROVENANCE.json cac8ad5f3ea7588c8baf066d2214163062d0aa68e8f47e1bca98c32de154c93c
```

The manifest's `provenance_sha256` is therefore a binding to the provenance object's recorded
snapshot hash (`6881cdf5...`), not the digest of the JSON serialization. Internal identifiers are
consistent, but the authoritative source snapshot could not be opened from this sandbox and git
was unavailable, so provenance accuracy and the non-copying assertion remain unverified.

`find` found 59 regular files, no symlinks/special files, no retained `build/` directory, and no file
larger than 1 MiB in the original. A bounded grep for common private-key headers, AWS/GitHub token
forms, and credential assignments found no match. The only external references found were the
catalog SSH URL and the linked article HTTPS URL in `PROVENANCE.json`.

An aggregate made by hashing the sorted per-file SHA-256 listing was identical before and after all
work:

```text
6a9644c3870a3bf28807e1ad2879e38256edf6fd51f50c15040190edb56642fb
```

Thus the original candidate was not modified. The scratch copy and temporary reviewer harness were
removed after recording results.

## Reproducibility check

Each kernel was hashed, cleaned with its scoped Makefile target, rebuilt, and hashed again. Results:

```text
starter build 1:   48b624037b4e6325ac50d25ab150b6934b4e983834300db67a450fc0afd9b926
starter build 2:   48b624037b4e6325ac50d25ab150b6934b4e983834300db67a450fc0afd9b926
reference build 1: 9d115ef1880dd5f3d1f2e973f74a359b777b50c37e882dde0f9018a2a11d220b
reference build 2: 9d115ef1880dd5f3d1f2e973f74a359b777b50c37e882dde0f9018a2a11d220b
```

This proves same-host, same-toolchain repeatability for these two builds only. It is not transfer
verification.

## Validation-label conclusion

The builder's substantive command results were reproducible, including the expected starter and
sanitizer failures. Its timing values understandably differed on rerun. The opaque final-policy
check in the candidate could not be reconstructed because its command/script is absent; the
independent scans above are narrower replacements, not confirmation of that prose claim.

No boot, sanitizer-clean, fuzz, generalized benchmark, external review, transfer, or production
claim was established. Retaining `GENERATED` and `PARTIAL` is honest; this review does not promote
the manifest.
