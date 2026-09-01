# Independent Rubric — IR/CFG Kickoff Unit

Classification: **EXAMINER ONLY**. Do not copy this file, its weights, evaluator probes, or scoring notes into `student_safe/`.

This rubric evaluates only `unit_kickoff_ir_cfg_reachability_v1`. A passing result is not evidence of completion of NJU Software Analysis or any later unit. Learner claims and prose alone are not evidence; inspect the submitted artifacts and reproduce the relevant behavior.

## Evaluation protocol

1. Record the submission identity and toolchain versions.
2. Build from a clean submission using the documented command, without network access.
3. Run the learner's complete automated test suite and preserve its output.
4. Run independent temporary fixtures covering valid, invalid, cyclic, and disconnected graphs. Do not add sealed fixtures to the learner view.
5. Run one valid fixture twice in fresh processes and compare standard output byte-for-byte.
6. Inspect source, `README.md`, `DESIGN.md`, and `COMPREHENSION_RESPONSES.md` rather than accepting self-reported behavior.
7. Record awarded points, concrete evidence, validation label, and any cap applied.

If the evaluator must execute the program through a harness, use an argument-vector subprocess, a bounded timeout, a fresh process group, and captured standard streams. Never interpolate the learner's path or input into a shell command.

## Scoring (100 points)

### A. Parsing and validation — 24 points

- **8:** Accepts the specified entry, block, ordinary-instruction, and three terminator forms, including comments and blank lines.
- **10:** Rejects malformed labels, duplicate/misplaced entry directives, duplicate blocks, instructions outside blocks, missing/multiple terminators, content after a terminator, empty required opaque text, and unknown targets without repairing the input.
- **4:** Diagnostics go to standard error, include an accurate line number and useful reason, and invalid input produces no partial JSON.
- **2:** Unreadable inputs and syntax/semantic failures use exit code `2`; valid input uses `0`.

### B. CFG semantics and reachability — 24 points

- **8:** Creates exactly the specified successor relation for `goto`, `branch`, and `return`, preserving true-before-false terminator meaning while deduplicating adjacency.
- **6:** Derives complete, duplicate-free predecessor relations, including joins, loops, and the same branch target used twice.
- **8:** Computes entry reachability correctly for chains, branches, joins, self-loops, multi-node cycles, and disconnected blocks; retains unreachable blocks.
- **2:** Traversal is cycle-safe and consistent with `O(V + E)` time after parsing.

### C. Deterministic output and CLI contract — 16 points

- **7:** Emits the required JSON fields with correct types and properly escaped valid JSON.
- **5:** Applies declaration order consistently to blocks and all label arrays while removing duplicates.
- **2:** Repeated fresh-process runs on the same input are byte-identical.
- **2:** Valid runs keep standard error clean and the CLI accepts exactly one input path with documented behavior for misuse.

### D. Software design and robustness — 16 points

- **6:** Parsing/source locations, semantic validation/model, graph analysis, serialization, and CLI adaptation have clear boundaries and can be tested below the process level.
- **4:** The validated model protects core invariants; error handling does not terminate deep inside reusable components; global mutable state is absent.
- **3:** IR text is treated as data: it is neither evaluated nor passed to a shell, and the analyzer performs no network access.
- **3:** Names, small functions/classes, comments, and build configuration make the implementation maintainable without unnecessary framework complexity.

### E. Test evidence — 12 points

- **6:** Automated tests cover the required cycle, unreachable block, duplicate-label, unknown-target, missing-terminator, and deterministic-output cases with meaningful assertions.
- **3:** Tests additionally exercise a join/predecessors, a duplicated branch target, comments/whitespace, and JSON escaping or equivalent risky boundaries.
- **3:** The full suite is deterministic, runs from the documented command, and fails when a checked contract is deliberately perturbed or otherwise demonstrates non-vacuous assertions.

### F. Design reasoning and comprehension — 8 points

- **3:** `DESIGN.md` accurately states boundaries, invariants, ordering and error choices, and complexity, matching the submitted code.
- **5:** All comprehension responses are technically coherent, use implementation/test evidence where requested, and distinguish current behavior from the unimplemented liveness extension.

## Caps and critical defects

- Cap at **69** if the project cannot be built from a clean submission with its documented command, or if the learner's full tests fail for reasons attributable to the submission.
- Cap at **69** if valid inputs cannot produce parseable JSON through the documented CLI.
- Cap at **59** if unknown targets are silently repaired, IR text is executed, the implementation invokes a shell with learner-controlled text, or the core traversal can fail to terminate on a valid cycle.
- Award **0 and flag for review** if the submission contains restricted solutions, sealed evaluator material, fabricated test logs, or code not attributable under the applicable learning policy. Do not infer misconduct merely from a defect or stylistic similarity.

Apply the lowest relevant cap after adding category points. Explain every cap with reproducible evidence.

## Validation decision

Label the unit **PASS** only when all of the following hold:

- the uncapped category total is at least 80;
- the final total after caps is at least 80;
- no critical defect or review flag applies;
- clean build, learner tests, and independent valid/invalid fixtures were actually run; and
- durable evidence identifies the evaluated submission and captured outcomes.

Otherwise label it **NOT_YET_PASSING** or **REVIEW_REQUIRED**, as appropriate. Only a validator controlled by the worker harness may use this rubric to promote job state.

---

Provenance: examiner-only, independently manager-authored rubric for the bounded kickoff unit. It was derived from the supplied task contract and repository validation invariants; no external course rubric, hidden grader, or restricted content was retrieved.
