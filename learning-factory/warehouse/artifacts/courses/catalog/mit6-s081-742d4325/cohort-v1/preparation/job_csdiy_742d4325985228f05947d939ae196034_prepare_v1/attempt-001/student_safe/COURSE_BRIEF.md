# Unit 0 — Build vmwalk, a Bounded Virtual-Address Translator

> Course: `course_742d4325985228f05947d939ae196034` — MIT 6.S081: Operating System Engineering  
> Unit: `unit_kickoff_vmwalk_v1`  
> Artifact provenance: course-manager-authored from the supplied CSDIY catalog snapshot; no linked content was retrieved.  
> Validation label: **PREPARED / NOT YET HARNESS-VALIDATED**

## What this unit is

This is a self-contained engineering kickoff for a learner who is already comfortable with algorithms and is building production-minded systems habits. You will implement a small C11 model from a precise contract, defend its boundaries, test it deterministically, and distinguish your own evidence from controlled validation.

This unit is not an MIT lab, does not reproduce an official MIT unit, and does not require xv6 or RISC-V tooling. Completing it can establish completion of this kickoff only. It cannot establish completion of MIT 6.S081 or of any larger course plan.

## Entry assumptions

You should be able to:

- write and compile a multi-file C program;
- use masks, shifts, arrays, and fixed-width integer types;
- explain hexadecimal notation and a virtual-to-physical mapping at a high level; and
- run `make` and inspect a process exit status.

The catalog lists Computer Architecture, solid C programming, and RISC-V assembly as course prerequisites. This kickoff directly exercises the first two; it does not assess RISC-V assembly.

## Outcomes

By the end of the timebox, you should be able to:

1. decompose a virtual address into two indices and an offset;
2. implement deterministic translation and permission behavior from a written contract;
3. separate modeled faults from malformed input and internal program failure;
4. enforce input limits and state invariants without undefined behavior; and
5. produce repeatable tests and honestly labeled engineering evidence.

## The model

`vmwalk` models a deliberately small two-level page table:

- A virtual address is 16 bits.
- Bits 15–12 select a level-one index (`L1`).
- Bits 11–8 select a level-two index (`L2`).
- Bits 7–0 are the page offset.
- A mapping at `(L1, L2)` contains an 8-bit physical page number (`PPN`) and a nonempty subset of read, write, and execute permissions.
- The physical address is `(PPN << 8) | offset`.
- A missing mapping produces an unmapped fault. A mapping without the requested permission produces a permission fault.

These are teaching rules for this artifact, not claims about xv6 or the RISC-V Sv39 implementation.

## Deliberate boundary

The unit excludes real page-table encodings, privileged instructions, TLBs, accessed or dirty bits, page allocation and replacement, concurrency, actual memory access, and xv6 integration. Do not install an emulator, fetch a source tree, or expand the task into a real kernel.

The catalog contains links to a website, lecture media, a textbook, assignments, and third-party resources. Their content is not present or verified here, and none is required for this unit.

## Timebox

Target five hours and stop after six hours:

- 15 minutes: read the contract and list ambiguities before coding;
- 30 minutes: choose representations and test cases;
- 2 hours 30 minutes: implement the parser and model;
- 1 hour: automate tests and inspect failure paths; and
- 45 minutes: clean-build, record evidence, and answer the comprehension prompts.

If the hard stop arrives, preserve what you have, label it `INCOMPLETE`, and identify the first failing command or exact blocker. A bounded, truthful handoff is preferable to unrecorded scope growth.

## Evidence boundary

Your build and test logs must be labeled `SELF-CHECKED`. They help another engineer reproduce your work, but they are not authoritative proof of completion. Only a controlled clean rerun by the worker harness may apply the `HARNESS-VALIDATED` label.
