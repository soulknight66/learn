---
course_id: course_186d33d93d0211917db009f374a278b6
unit_id: unit_01_minicool_lexer_engineering
audience: learner
provenance: manager-authored kickoff based on source-derived CSDIY catalog metadata at commit adce8e13789dc16aa6d1fbe163e9541736defae4
validation_label: LEARNER_SAFE_PREPARED_UNVALIDATED
---

# Stanford CS143: Compilers — bounded kickoff

This packet starts one small, engineering-focused study unit: design and build a lexer for a deliberately limited language called **MiniCOOL-0**. The catalog describes a much larger compiler course covering the frontend, runtime systems, optimization, code generation, and a COOL-to-MIPS project. This packet does not reproduce that course or any official assignment.

The unit is written for a student who is already comfortable with algorithms, asymptotic reasoning, data structures, and basic computer architecture. Use Java or C++. The point is to turn that foundation into reliable software: a precise contract, clean component boundaries, deterministic behavior, reproducible builds, automated tests, and evidence-backed explanations.

## What this unit covers

By the end of the timebox, you should be able to:

- model lexical analysis as a deterministic, position-aware pass over source text;
- implement longest-match tokenization and explicit error recovery;
- keep scanner logic separate from command-line I/O and diagnostics;
- test interactions among identifiers, operators, comments, strings, and malformed input;
- explain complexity and correctness using evidence from your own code and tests.

The scanner contract is fully specified in `STUDY_TASK.md`; no external course link or textbook is required.

## Boundaries

Included: a MiniCOOL-0 token contract, implementation, CLI, automated tests, design notes, and comprehension prompts.

Excluded: claims of full COOL compatibility; parsing; type checking; runtime layout; register allocation; optimization; MIPS generation; SPIM execution; and every official Stanford assignment, lab, lecture, or credential.

MiniCOOL-0 is manager-authored for this exercise. Similar names provide compiler-course context, not official status or compatibility.

## Suggested timebox

| Work | Target |
|---|---:|
| Contract reading and design sketch | 1 hour |
| Scanner and CLI implementation | 3–4 hours |
| Test design and defect fixing | 2 hours |
| Documentation and comprehension | 1 hour |

Stop after 8 hours and document unfinished edges honestly. A well-characterized limitation is better evidence than an unsupported completion claim.

## Evidence and completion

Keep implementation, tests, and documentation together in a small repository. Record the exact clean-build and test commands. Your written explanation should cite file paths, test names, or observed command output.

Submitting work does not itself complete the unit. An independent worker-harness validator must run the documented commands and apply the examiner rubric. Even a validated pass completes only this kickoff unit; it is not evidence of completing Stanford CS143 or a full compiler course.

## Material status

The source snapshot supplied catalog metadata and external pointers, not copies of lectures, a textbook, official assignment prompts, or repository contents. Those items were not retrieved. This learner packet is the complete material needed for the bounded unit.
