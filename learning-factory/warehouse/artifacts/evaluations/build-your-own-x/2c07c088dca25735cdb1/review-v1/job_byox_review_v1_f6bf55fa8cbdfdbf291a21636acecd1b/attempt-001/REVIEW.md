# Independent review

Verdict: **REVISE**.

The pack is unusually candid and useful as an educational artifact: the pure C reference passes
both supplied and independent checks, the starter fails visibly, and the documentation keeps
build, host-test, boot, benchmark, and production evidence separate. Two defects in the emitted
kernel nevertheless make the sealed reference unsafe to accept as correct without revision.

## Prioritized findings

### High — host compiler defaults inject SSE2 into the IRQ path

The freestanding flags in `starter/Makefile` and `sealed/reference/Makefile` select `-m32`, but do
not select an ISA baseline or prohibit compiler use of floating-point/SIMD registers. On the stated
GCC 8.5 toolchain, `gcc -m32 -Q --help=target` reports `-march=x86-64` with MMX, SSE, and SSE2
enabled. Disassembly of the independently rebuilt reference contains:

```text
101861: f3 0f 7e 03       movq (%ebx),%xmm0
101865: 66 0f d6 04 c8    movq %xmm0,(%eax,%ecx,8)
```

These instructions implement the event copy in `keyboard_queue_push_isr`. The boot path never
establishes the required CR0/CR4 SIMD state, and `keyboard_isr_stub` uses only `pusha`/`popa`, so it
does not preserve XMM state. A bootloader is not a valid implicit SIMD initializer. Depending on
entry state, the first accepted keyboard event can fault; even where SIMD happens to be enabled, the
ISR can corrupt an interrupted client's XMM0.

Set and document an explicit kernel CPU policy. For a baseline integer-only kernel, use suitable
`-march`/`-mno-sse`/`-mno-mmx`/soft-float flags for every kernel-linked translation unit and add an
artifact check rejecting forbidden register/instruction use. Alternatively, initialize and manage
SIMD state and preserve it across interrupts. A diagnostic compile with `-march=i386`, `-mno-sse`,
`-mno-mmx`, and `-msoft-float` succeeded here without SIMD register references.

### High — `.bss` is linked at different virtual and physical addresses

`readelf -l` and `objdump -h` show this independently rebuilt reference layout:

```text
.bss VMA 00103000, LMA 001057c0, size 000048a0
LOAD offset 0x004000, VirtAddr 0x00103000, PhysAddr 0x001057c0,
     FileSiz 0x00000, MemSiz 0x048a0
```

The code runs without paging and references the VMA symbols directly, while a Multiboot ELF loader
uses load-segment physical addresses. This mismatch means the linker artifact does not express the
flat physical-equals-virtual layout the boot code assumes. Some currently important zero-initialized
objects happen to fall in the overlapping ranges, but that accident is neither a valid layout nor
stable as the BSS changes.

Make VMA and LMA intent explicit in the linker script/PHDRs and test every allocated segment, not
only the ELF identification and Multiboot magic. The existing verifier reports PASS without parsing
program headers, so it cannot catch this defect.

### Medium — the manifest does not directly bind the delivered provenance object

The delivered values are:

```text
MANIFEST.yaml provenance_sha256:       14e4683c18c49bf52fffb640c2fcdf5df5df77986fbd27a25863624dd7d3799d
PROVENANCE.json raw SHA-256:            91899132ac13e14aa97483f8b9d76b1788bb7aa5d86ac5ba43ff6d814c6191d2
PROVENANCE.json canonical-JSON SHA-256: d904f811cf8c6ea3d20abff468ccd266a7778a9a49dbe6efb9d2c42b4eef3fac
```

The manifest value merely repeats `PROVENANCE.json.snapshot_sha256`. The artifact-owned audit knows
the canonical digest because it hard-codes it, but that script is not an independent trust anchor
and the manifest field named `provenance_sha256` cannot verify either delivered representation.
Define the digest domain unambiguously and bind the actual provenance object from the manifest.

The provenance also embeds an internal absolute source path containing the local user/workspace
layout. Retain portable source identity (`source_id`, URL, commit, tree hash) and omit host-specific
paths from a distributable artifact.

### Medium — complete ELF bytes depend on the build output path

Two builds from byte-identical source and object contents, but with `BUILD=.../reference-kernel` and
`BUILD=.../reference-kernel-2`, produced different complete files:

```text
c2583ba0...  reference-kernel/kernel.elf
74f9de35...  reference-kernel-2/kernel.elf
```

The loadable `.text` section was identical (`98460ea9...`), and the observed difference came from a
build path retained as a `FILE` symbol for `boot.o`. This is build-location sensitivity, not evidence
that executable bytes vary. State which reproducibility level is promised; if complete-file hashes
are intended as artifacts, normalize/strip non-loadable metadata and pin the compiler/binutils
target policy. The missing target policy is also what exposed the SSE issue above.

### Low — disclosure and generated-material licensing need an external boundary

Learner-facing files avoid solution answers and place references, deeper tests, answers, review,
tradeoffs, and production notes under `sealed/`. That is good progressive structure, but everything
under `sealed/` is physically readable in this submitted tree. The learner contract is not an
isolation mechanism. The worker harness must project an allowlisted learner view and test that no
sealed file crosses it.

The CC0 catalog and `NOASSERTION` linked-article boundary are clearly and honestly distinguished,
and no upstream copying was observed within the available evidence. The generated pack itself has
only a “personal educational use” description, not an explicit license grant, so redistribution and
reuse rights remain undefined. Add a generated-material license if sharing is intended.

## Supported strengths

- Requirements R1–R6 are concrete and consistently referenced.
- The terminal/decoder/queue reference passed 532 sealed checks, public tests, deterministic stress,
  and a separate reviewer model/concurrency harness.
- The starter links but fails 76 public assertions as documented; its TODOs are not disguised as a
  passing implementation.
- Concepts, design questions, debugging prompts, review exercises, tradeoffs, and limitations make
  the pack useful beyond “make the tests green.”
- The candidate correctly calls its stress run deterministic rather than fuzzing, provides no fake
  benchmark number, marks productionization false, and explicitly disclaims boot evidence.

## Acceptance criteria

Rebuild with a deliberate kernel ISA/state policy, prove the artifact contains no unintended SIMD
in interrupt-reachable code, correct and validate the ELF load layout, and make the provenance hash
domain verifiable. Then rerun host/model/concurrency tests plus an emulator boot that injects key
make/break/modifier sequences and observes display/queue behavior. Keep the current PARTIAL status
until that independent boot evidence exists.
