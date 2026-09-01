# Independent validation record

Date: 2026-08-31 (America/Chicago). Commands ran from the review workspace root unless a `-C`
argument says otherwise. `CANDIDATE/` remained read-only; all compiler outputs used a temporary
`.review-build/` directory outside it. The sandbox printed benign user/group name-resolution
warnings before many commands; those are omitted below.

No observation in this file promotes the candidate's manifest or establishes a factory validation
label.

## Environment and unavailable tools

```text
$ python3 --version
Python 3.6.8

$ gcc --version | head -1
gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)

$ make --version | head -1
GNU Make 4.2.1

$ ld -v
GNU ld version 2.30-123.el8
```

Direct `command -v` checks found `gcc`, `make`, `ld`, `readelf`, `nm`, `objdump`, and `python3`.
They did not find `qemu-system-i386`, `grub-file`, `grub-mkrescue`, `xorriso`, `clang`,
`scan-build`, `cppcheck`, or `valgrind`. Initial discovery also found `git` and `rg` unavailable.

The first Make attempts redirected `BUILD` outside the immutable tree but inherited a relative GCC
temporary directory. They stopped before compilation with:

```text
Cannot create temporary file in ./: Permission denied
```

This was a review-harness setup failure, not a candidate result. Every compilation below was rerun
with `TMPDIR="$PWD/.review-build/tmp"`; no candidate file was changed.

## Structure, metadata, and provenance

```text
$ (cd CANDIDATE && python3 environment/audit_artifact.py)
required regular files: 23/23
forbidden paths present: 0
manifest exact object: True
provenance exact canonical object: True
symlinks in generated scope: 0
credential-shaped matches in generated text: 0
artifact audit: PASS
exit 0
```

This is a candidate-owned audit and is only corroborative. Independent strict JSON parsing rejected
duplicate keys and accepted both metadata objects. Independent file/canonical hashing observed:

```text
$ sha256sum CANDIDATE/MANIFEST.yaml CANDIDATE/PROVENANCE.json
c1032298e7c98f5487f5d6f888ed93590c1f934481ae6e19e85ea0b15aee5c04  CANDIDATE/MANIFEST.yaml
91899132ac13e14aa97483f8b9d76b1788bb7aa5d86ac5ba43ff6d814c6191d2  CANDIDATE/PROVENANCE.json

$ python3 -c '...canonical json.dumps(...); sha256(...)'
d904f811cf8c6ea3d20abff468ccd266a7778a9a49dbe6efb9d2c42b4eef3fac
```

Neither provenance digest equals the manifest's `provenance_sha256` value `14e4683c...`; that value
equals the provenance object's internal `snapshot_sha256`. A scan found one internal absolute
project path at `PROVENANCE.json:78`. There were 73 regular files, no symlinks, no writable candidate
files, and the aggregate sorted file-content digest was:

```text
17b5c5d15beff128c5b13fa004837c1b931bbcffd615a3151f0edeb8fcab3cf1
```

An independent local Markdown-link check found one local link and no broken target. An uppercase
validation-label scan found only explicit statements that `FUZZED` and `BENCHMARKED` are not
claimed.

## Supplied host tests

All commands had a 45-second timeout.

```text
$ env TMPDIR="$PWD/.review-build/tmp" \
    make -C CANDIDATE/sealed/reference_tests \
    BUILD=../../../.review-build/reference_tests run
reference tests: PASS (532 checks)
exit 0

$ env TMPDIR="$PWD/.review-build/tmp" \
    make -C CANDIDATE/public_tests \
    BUILD=../../.review-build/public-reference PROJECT=../sealed/reference run
public tests: PASS
exit 0

$ env TMPDIR="$PWD/.review-build/tmp" \
    make -C CANDIDATE/sealed/adversarial \
    BUILD=../../../.review-build/adversarial run
adversarial stress: PASS (2209848 invariant checks)
exit 0
```

The stress harness was inspected: it uses a fixed xorshift seed and invariant/model checks. Its two
decoder instances run the same implementation, so their agreement checks determinism rather than an
independent decoder oracle. The candidate accurately avoids calling this fuzzing.

The unmodified starter's public run compiled, then visibly failed:

```text
$ env TMPDIR="$PWD/.review-build/tmp" \
    make -C CANDIDATE/public_tests \
    BUILD=../../.review-build/public-starter PROJECT=../starter run
public tests: 76 failure(s)
exit 2
```

That is the documented initial learner state, not a reference failure.

## Reviewer-authored pure-logic checks

A transient reviewer C harness (source SHA-256
`82720ce1f41ce046049de1697c1a65c461af44c1b10c43b19ff074a32cdb01f5`) was compiled directly
against `sealed/reference/src/terminal.c` and `keyboard.c` with C11, strict warnings, `-O2`, and
`-pthread`. It independently:

- compared 140,000 fixed-seed terminal operations across 35 small geometries to a separate content
  model while checking both guard cells after every operation;
- exercised unsupported/prefix, dual-shift, and Caps/Shift decoder sequences; and
- transferred 100,000 numbered events through simultaneous producer/consumer threads, checking
  exact FIFO payloads, retry/drop accounting, and empty-pop output preservation.

```text
$ timeout 30s .review-build/reviewer_checks   # repeated three times
reviewer checks: PASS (700060 checks, 100000 concurrent events)
reviewer checks: PASS (700060 checks, 100000 concurrent events)
reviewer checks: PASS (700060 checks, 100000 concurrent events)
all exits 0
```

This strengthens the pure-state-machine evidence. Hosted pthread execution still does not model
privileged single-core interrupt entry exactly.

## Freestanding builds and ELF inspection

```text
$ env TMPDIR="$PWD/.review-build/tmp" \
    make -C CANDIDATE/sealed/reference \
    BUILD=../../../.review-build/reference-kernel kernel
exit 0

$ env TMPDIR="$PWD/.review-build/tmp" \
    make -C CANDIDATE/starter BUILD=../../.review-build/starter-kernel kernel
exit 0

$ python3 CANDIDATE/environment/verify_kernel.py \
    .review-build/reference-kernel/kernel.elf
kernel verification: PASS (ELF32 i386, valid Multiboot-v1 header at file offset 4096)
exit 0
```

An independent Python parser found the aligned header tuple at offset 4096 and verified its
32-bit checksum. `readelf -h` reported ELF32, little-endian, ET_EXEC, Intel 80386, entry
`0x101000`. `readelf -r` reported no relocations, and `nm -u` printed no undefined symbols. Direct
strict freestanding i386 object compiles of `sealed/alternatives/polling_input.c` and
`sealed/production/event_loop.c` both exited 0.

Program-header inspection exposed a result that the candidate verifier does not check:

```text
$ readelf -l .review-build/reference-kernel/kernel.elf
LOAD 0x001000  VirtAddr 0x00100000  PhysAddr 0x00100000  FileSiz 0x022c0  MemSiz 0x022c0  R E
LOAD 0x004000  VirtAddr 0x00103000  PhysAddr 0x001057c0  FileSiz 0x00000  MemSiz 0x048a0  RW

$ objdump -h .review-build/reference-kernel/kernel.elf
.bss  size 000048a0  VMA 00103000  LMA 001057c0  file offset 00004000
```

The starter has the same class of mismatch (`.bss` VMA `0x103000`, segment physical address
`0x105fb8`). No boot result can be inferred from the structural verifier.

## Unintended SIMD in the kernel

```text
$ gcc -m32 -Q --help=target | grep -E '^  -m(arch|tune|sse|sse2|mmx)'
-march= x86-64
-mmmx [enabled]
-msse [enabled]
-msse2 [enabled]
-mtune= generic

$ objdump -d .review-build/reference-kernel/kernel.elf | \
    grep -nE '%(xmm|ymm|zmm|mm[0-7])'
728: 101861: f3 0f 7e 03       movq (%ebx),%xmm0
729: 101865: 66 0f d6 04 c8    movq %xmm0,(%eax,%ecx,8)
exit 0
```

Those instructions are in `keyboard_queue_push_isr`. Disassembly of `keyboard_isr_stub` shows
`pusha; cld; call keyboard_isr_c; popa; iret`, with no XMM preservation. A source scan found no CR0,
CR4, FXSAVE/FXRSTOR, SSE, MMX, or XMM state setup. As a diagnostic only, compiling `keyboard.c`
with `-march=i386 -mno-sse -mno-mmx -msoft-float` succeeded and produced no SIMD register match.

## Build-location sensitivity

A second reference build used the same sources, flags, and toolchain but a different `BUILD` path.
All six corresponding input object files were byte-identical. Complete linked files were not:

```text
$ sha256sum .review-build/reference-kernel/kernel.elf \
    .review-build/reference-kernel-2/kernel.elf
c2583ba04270db37685f9bcecef44c467998c4b5f84a53c7d56ff2d25b8b5186  .../reference-kernel/kernel.elf
74f9de35fc677caad586734afdeb22df45571bafb532cccebf0300dbbb398178  .../reference-kernel-2/kernel.elf

$ cmp -s .../reference-kernel/kernel.elf .../reference-kernel-2/kernel.elf
exit 1
```

`strings` showed the respective `.../reference-kernel/boot.o` paths embedded as symbol-table file
names. Extracted `.text` sections were identical in both files:

```text
98460ea9bdcbe2cfcecf9f4d3775b9ed6be9e6aafe52252dc3353e208a42baf3
```

Thus executable text reproduced, while the complete ELF is sensitive to its build directory.

## Blocked checks and evidence boundary

Both supplied sanitizer targets reached the link step and failed as documented:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
exit 2
```

No QEMU/GRUB/ISO tool was present. Consequently there was no emulator boot, scan-code injection,
visual screen check, or real IRQ/PIC observation. There was also no physical-hardware, benchmark,
fuzzing, profiler, security, transfer, portability, or production-readiness result. The catalog
source repository and linked article were outside the permitted workspace, and `git` was absent, so
the recorded commit/snapshot/license evidence and no-copy claim remain unverified rather than
failed.
