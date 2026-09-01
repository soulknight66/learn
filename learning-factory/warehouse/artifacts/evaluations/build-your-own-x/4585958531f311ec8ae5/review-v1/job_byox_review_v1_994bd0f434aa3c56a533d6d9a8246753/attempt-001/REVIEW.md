# Independent review

Verdict: **REVISE**. The bounded host implementation is coherent and the candidate is unusually
careful about not overstating its validation. Two release-boundary issues should be resolved before
acceptance: learner isolation is not represented deterministically, and repeat VM initialization
has an undocumented ownership consequence.

## Prioritized findings

### P1 — The submitted material does not establish a safe learner view

The bundle contains a complete implementation, deeper tests, design answers, debugging answers,
review answers, and evaluator commentary under readable paths in `CANDIDATE/sealed/`. The only
learner-side control visible here is the prose instruction not to inspect that directory
(`CANDIDATE/AGENTS.md:10`). `CANDIDATE/VALIDATION.md:72` reports
`learner_answer_path_check=0`, but supplies neither the command nor an exported path list. That
builder-authored result cannot prove isolation.

This layout may be appropriate for an evaluator bundle, but it is not safe to hand to a learner as
one tree. Add a deterministic, testable student-view allowlist/export manifest (or split learner and
validator artifacts), then demonstrate that no `sealed/` path, answer, hidden test, or compiled
solution is present in the exported view. Keep the current evaluator bundle separate.

### P1 — `tk_vm_init` has an undocumented repeat-call resource leak

The public contract says `tk_vm_init` “removes all mappings and records the allocator” without a
fresh-object precondition (`CANDIDATE/REQUIREMENTS.md:35`). The reference implementation clears
each mapping but never returns already owned frames (`CANDIDATE/sealed/reference/src/vm.c:5`). An
independent probe observed:

```text
mappings_before=1 free_before=1 mappings_after=0 free_after=1
```

The address space is empty after the second initialization, yet one of its two frames is no longer
reachable for unmapping. The sealed review acknowledges this as an initializer-only limitation,
but learners cannot use a sealed note to disambiguate their public contract.

Choose and document one model: explicitly make initialization valid only for fresh/uninitialized
storage, or add a separate reset/destroy operation that releases mappings before clearing them.
Add a regression test for the chosen lifecycle. An initializer cannot safely inspect arbitrary
uninitialized storage, so a distinct reset API is the clearer option.

### P2 — The generated material has provenance prose but no explicit license grant

`LICENSE_BOUNDARY.md` correctly keeps the catalog's CC0 status separate from the linked article's
`NOASSERTION` status and does not infer rights from the article. However, “independently generated
for personal educational use” describes origin and intended use; it does not grant a license for
learners to copy, modify, or redistribute the generated code and text. Add an explicit license (and
SPDX identifier where appropriate), or state clearly that no redistribution license is granted.
This does not undermine the otherwise careful upstream boundary.

### P2 — ELF format validation is narrower than its success message suggests

`environment/check_elf.py` checks class, endianness, machine, nonzero entry, and the presence of the
four magic bytes. It does not validate Multiboot flags/checksum, whether the entry lies in an
executable load segment, or the physical load layout. Independent inspection found that the actual
header triple is checksum-valid and the entry is executable, but GNU `ld` 2.30 emitted BSS segments
whose `p_paddr` differs from `p_vaddr` in both images. No available loader could determine the
runtime consequence.

Keep this result described as an ELF structural check, not boot evidence. Strengthen the checker to
parse the full Multiboot header and load segments, and add a bounded GRUB/QEMU smoke test when that
toolchain is available. The current manifest correctly avoids a boot or BUILDS promotion.

## Confirmed strengths

- The four-stage requirements, starter loop, concepts, and design prompts form a useful progressive
  learning path once the sealed material is actually excluded from the learner view.
- Public tests are explicitly presented as examples, and the starter's 27 failures clearly show
  that producing an ELF is not confused with completing the behavioral exercise.
- Reference public tests, sealed edge tests, and audit-prototype tests all passed independently.
  A reviewer-authored harness also passed 178 unambiguous edge and failure-atomicity checks at
  default and `-O2` optimization.
- Both freestanding images linked without libc or unresolved symbols. Two clean builds of each were
  byte-identical on the review host.
- The candidate accurately recorded its unavailable sanitizer libraries. Its benchmark prose is
  appropriately limited; five independent samples completed but had variable timing.
- `MANIFEST.yaml` remains `GENERATED` + `PARTIAL`, requires independent validation, and says
  `productionized: false`. The production assessment is candid about major missing kernel features.
- Metadata identifiers are internally consistent, and a bounded credential-pattern scan found no
  match. The upstream linked-resource license remains `NOASSERTION` throughout.

## Disposition

Resolve the student-view boundary and VM lifecycle contract before acceptance. The license and ELF
checker findings are lower priority but should be addressed before redistribution or any stronger
validation label. Nothing in this review supports FUZZED, BENCHMARKED, boot-verified,
TRANSFER_VERIFIED, or PRODUCTIONIZED.
