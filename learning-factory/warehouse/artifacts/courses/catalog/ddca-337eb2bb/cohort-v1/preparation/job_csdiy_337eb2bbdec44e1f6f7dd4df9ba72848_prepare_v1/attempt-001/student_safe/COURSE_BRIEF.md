# Digital Design and Computer Architecture: kickoff brief

## What this is

This is a five-hour, manager-authored kickoff for *Digital Design and Computer Architecture*. You will treat a small combinational circuit as a software component: define its contract, build it from a smaller component, test its complete finite input space, and leave reproducible evidence.

This is not an ETH Zurich lecture, lab, or assignment. Completing it does not complete the cataloged course, any official course unit, or any of the nine labs mentioned in the catalog.

## Why this unit comes first

Algorithms experience transfers well to reasoning about invariants and composition. Digital design adds constraints that ordinary programs can hide: fixed-width values, explicit carry information, small interfaces, and dependencies between stages. A four-bit ripple-carry adder makes those constraints visible while remaining small enough to verify exhaustively.

The engineering habits are equally important: an unambiguous interface, an independent oracle, deterministic tests, input-boundary checks, a repeatable command, and evidence that distinguishes observation from assertion.

## Outcomes

By the end of this kickoff, you should be able to:

- express one-bit addition as a finite behavioral contract and Boolean logic;
- compose four stages without replacing the design with whole-number arithmetic;
- test every valid input against an independently expressed reference model;
- document invalid-input policy, design decisions, and traceability;
- explain functional correctness separately from carry-chain cost; and
- report what was actually run, including limitations or failures.

## Prerequisites and tools

You need basic programming, binary-number familiarity, and Python 3 with its standard library. You do **not** need Verilog, Vivado, an FPGA board, a textbook, a recording, or access to the external course site for this unit.

The catalog contains external links and book citations, but their contents were not retrieved or verified for this kickoff. Do not infer required pages or lectures from those pointers. If a linked resource is unavailable, continue with the local task; it is intentionally self-contained.

## Timebox

Use approximately:

- 20 minutes to read and restate the contract;
- 60 minutes for the truth table, equations, and design note;
- 60 minutes for implementation;
- 75 minutes for exhaustive and boundary tests;
- 45 minutes for cleanup and reproducibility evidence; and
- 40 minutes for the comprehension responses.

Stop after the defined artifacts. Cache design, pipelining, Verilog/FPGA synthesis, MIPS, and virtual memory belong to possible later units and are out of scope here.

## Working order

1. Read `STUDY_TASK.md` fully and create a clean project layout.
2. Write the contract and design reasoning before implementation.
3. Implement the one-bit component, then compose the four-bit component.
4. Build tests from the public contract rather than copying production logic.
5. Run from a clean project root and record the real outcome in `EVIDENCE.md`.
6. Answer the prompts in `COMPREHENSION.md` in your own `answers.md`.

Your submission is evidence for review, not a self-certification of completion. An independent examiner and the learning-factory validator make that decision.
