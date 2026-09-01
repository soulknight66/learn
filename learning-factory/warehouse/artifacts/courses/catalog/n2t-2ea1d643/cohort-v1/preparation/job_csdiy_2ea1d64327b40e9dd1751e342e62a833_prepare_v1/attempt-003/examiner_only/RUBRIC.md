# Independent Rubric: NAND Component Engineering Kickoff

This rubric is examiner-only. Grade the submitted artifact, not the learner's confidence or prose claim. Do not require access to Coursera, recordings, the textbook, a catalog-linked repository, or an official Nand2Tetris toolchain. The exercise is manager-authored and platform-neutral.

## Evaluation procedure

1. Work from the final `submission/` contents in a clean or isolated environment.
2. Check that the documented test command is bounded, non-interactive, and does not require network access.
3. Run it and retain its exit status and output as examiner evidence.
4. Inspect implementation source independently for the structural constraint; tests alone cannot establish it.
5. Compare captured learner evidence with the final source and the examiner's run.
6. Score the five categories below, then apply critical-failure rules.

## Reference behavior

Use strict Boolean values for this reference. `nand(a,b)` is false only for `(true,true)`. NOT returns the complement of its input. AND is true only when both inputs are true. OR is true when either input is true. `mux2(a,b,select)` returns `a` for false selection and `b` for true selection.

A valid construction can be formed entirely from NAND calls; equivalent compositions are acceptable. The `nand` primitive alone may use host-language operators. In derived component bodies, calls, assignment, local naming, and returns are permitted, while logical or bitwise operators, arithmetic, conditionals, pattern matching, answer-producing casts, lookup tables, and library gate implementations violate the task constraint.

## Scoring (100 points)

### 1. Functional correctness — 25 points

- **5:** `nand` matches all four Boolean input pairs.
- **4:** `not_gate` matches both inputs.
- **4:** `and_gate` matches all four input pairs.
- **4:** `or_gate` matches all four input pairs.
- **8:** `mux2` matches all eight `(a, b, select)` triples, including cases where `a` and `b` differ.

Award a component's points only when examiner-run evidence covers its entire stated Boolean domain. If the submission documents acceptance of `0` and `1`, equivalent outputs are acceptable; inconsistent or surprising coercion is assessed under category 4.

### 2. Composition and design integrity — 20 points

- **10:** All four derived component bodies obey the NAND-only construction constraint. Deduct 3 points per affected derived component, to a minimum of zero for this item.
- **4:** The NAND primitive is isolated and derived/public interfaces are easy to locate and audit.
- **3:** The documented dependency DAG is accurate and acyclic.
- **3:** Names and intermediate structure communicate intent without hidden behavior or unnecessary coupling.

Static source inspection is required. A passing truth table does not earn the first item if the source bypasses the construction constraint.

### 3. Deterministic verification — 25 points

- **10:** Tests enumerate the required 4 NAND, 2 NOT, 4 AND, 4 OR, and 8 multiplexer cases, with useful failure identification.
- **5:** Expected values are an independent oracle rather than values computed through the implementation under test or an equivalent shared bug.
- **4:** Tests cover and agree with the documented invalid-input policy; a clearly justified strict-Boolean policy may reject all other values.
- **4:** Mutation evidence identifies a plausible temporary fault, includes an actual failing result, and is consistent with a restored final passing run.
- **2:** Repeated examiner runs are deterministic and have no order, time, randomness, or network dependency.

Do not award points merely for a list of claimed cases; inspect test discovery/output or otherwise establish that the cases execute.

### 4. Reproducibility and repository quality — 15 points

- **5:** One documented command runs the complete suite from the stated starting directory and exits zero on the examiner's clean run.
- **3:** Runtime/tool version and any requirements are explicit; setup is bounded and does not conceal undeclared dependencies.
- **3:** Required source, tests, design, evidence, and responses are present in the requested layout, while generated or sensitive material is absent.
- **2:** Captured final output states the command and agrees materially with the examiner's run and final source.
- **2:** Interface and invalid-input behavior are unambiguous and consistent across README, implementation, and tests.

### 5. Engineering reasoning and comprehension — 15 points

Score the eight numbered responses together:

- **13–15:** Specific, technically sound answers grounded in submitted artifacts; clearly distinguishes behavioral from structural evidence, limits exhaustive-testing claims, analyzes mutation and language risks, proposes credible scaling techniques, and preserves the unit boundary.
- **9–12:** Mostly correct and artifact-specific, with one or two shallow or imprecise explanations.
- **5–8:** Partial understanding; several generic answers, weak evidence links, or overclaims.
- **1–4:** Minimal responses with substantial misconceptions.
- **0:** Missing, copied, or non-responsive.

## Critical failures and caps

- **No runnable implementation or complete test command:** not passable; cap the total at 59.
- **Any required component is functionally incorrect in the examiner's exhaustive run:** not passable; cap at 69.
- **A derived component materially bypasses the NAND-only constraint:** not passable; cap at 69.
- **Examiner command hangs, requires interactive input, or requires undeclared network access:** not passable; cap at 69.
- **Captured evidence is materially inconsistent with the final artifact:** award no mutation/evidence points and cap at 69 if the inconsistency presents a false passing claim.
- **Submission includes secrets, restricted course content, examiner-only material, or another learner's work:** stop normal grading, preserve evidence, and refer for integrity review; do not mark complete.

Apply the lowest applicable cap after ordinary scoring.

## Decision

- **Complete this kickoff unit:** at least 80/100 after caps, no critical failure, and a passing examiner-run exhaustive suite.
- **Not yet complete:** any other result. Return category-level findings and reproducible failure evidence.

A complete decision applies only to `kickoff_nand_component_engineering_v1`. It is not evidence of an official Nand2Tetris assignment, either Coursera course part, or whole-course completion.
