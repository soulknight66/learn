# Independent review

Advisory verdict: **REVISE**. The core exercise is useful, the reference's
semantic behavior is strong, and nearly all submitted build evidence was
reproducible. One direct contract defect and two reproducibility/learner-contract
gaps should be corrected before acceptance.

## Prioritized findings

### P1 — RAMFS initialization is not deterministic over the public object

`REQUIREMENTS.md:15-16` promises that initializers fully establish deterministic
state even when an input object previously held arbitrary bytes. Yet
`starter/src/ramfs.c:3-20` and
`sealed/reference/src/ramfs.c:3-15,85-95` clear only named members.

On the configured x86_64 ABI, `fs_file_t` is 304 bytes and its `size` member
starts at offset 296. The byte array ends at offset 289, leaving seven padding
bytes per file. A reviewer-authored check filled two `ramfs_t` objects with
different patterns, called `fs_init`, and compared their complete object
representations. It failed at byte 289 (`0xa5 != 0x5a`). The starter therefore
ships an already-implemented initializer that cannot meet its published
determinism promise; `clear_file` also leaves the same bytes intact on unlink.

This escaped the submitted suites because their initializer and unlink checks
inspect named fields only. Either clear the complete object representation in a
freestanding-safe way and add a regression test, or narrow the published
contract and the “full slot clearing” claims to semantic members. The current
combination is internally inconsistent.

### P2 — The zero-length `fs_write` null-buffer rule is not published

`REQUIREMENTS.md:80-84` says a zero-length write is valid but does not say
whether `data == NULL` is allowed. By contrast, lines 86-88 explicitly grant
that exception for `fs_read`. The reference accepts a null write buffer when
`count == 0`, and the sealed contract suite expects that result.

A learner can reasonably apply the general required-pointer rule and reject
the call, then fail evaluator behavior that was never stated. Publish the same
conditional-null rule for `fs_write`, or change the reference expectation.

### P2 — The hosted linker is selected implicitly, not from the recorded toolchain

`environment/README.md:3-10` and `VALIDATION.md:8-10` emphasize provisioned,
absolute-path tools, but `environment/toolchain.mk` records only the host GCC
driver. An independent `-Wl,--version` probe showed that hosted tests actually
use `/usr/bin/ld` 2.30-123.el8. Removing `PATH` made the absolute GCC link fail
with `cannot find 'ld'`; making the configured Binutils 2.43 directory available
made it succeed.

Record and select the exact host assembler/linker (for example through a
documented GCC `-B` prefix) and include its version in evidence. This closes the
gap between the reproducibility claim and the actual hidden host dependency.

## What was independently corroborated

- The starter is warning-clean and intentionally reports 1/5 public groups
  until learners implement its TODOs.
- A bounded clean reference build passed all 7 hosted groups and all three
  4,000-operation deterministic sequences. The freestanding AArch64 image
  linked without unresolved symbols and printed `MINIOS: PASS` under QEMU.
- A separate semantic suite exercised validation priority, scheduler
  transitions, VM bounds/permissions/capacity, RAMFS name and range bounds,
  sparse writes, and rejected-operation atomicity. It passed normally and under
  ASan/UBSan.
- Progressive disclosure is well organized: all 18 answer-bearing/reference
  files found by the independent scan are under `sealed`, prompts remain
  outside those directories, and the only non-sealed C files are starter/public
  material.
- Provenance identifiers are internally consistent. The license boundary is
  explicit about `NOASSERTION` for the linked resource and does not claim copied
  upstream content or broader rights. Validation labels remain honestly limited
  to `GENERATED` and `PARTIAL`.
- The requirements, concepts, design questions, debugging prompts, and finite
  public tests form a coherent and appropriately scoped learner progression.

## Review limitations

The upstream snapshot was unavailable, so non-copying and external license
claims could not be compared independently. No projected learner view was
provided, so filesystem placement—not end-to-end harness isolation—was checked.
LeakSanitizer was disabled because ptrace is unavailable; ASan and UBSan still
ran successfully. No physical-board, fuzzing, benchmark, production, or
transfer claim was evaluated or promoted.

Only a separate orchestrator-captured acceptance validator may publish a
`REVIEWED` label.
