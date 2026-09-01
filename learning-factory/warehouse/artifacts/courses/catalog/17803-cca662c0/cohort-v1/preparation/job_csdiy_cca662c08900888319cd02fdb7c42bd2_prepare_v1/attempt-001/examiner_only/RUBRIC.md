# Independent Examiner Rubric — Kickoff Unit 1

*Provenance: course-manager-authored examiner artifact. Validation label: examiner-only rubric, pending harness validation; not official CMU content.*

## Scope and evidence rule

This rubric evaluates only the manager-authored unit **From Benchmark to Defensible Claim**. A passing submission records unit-level progress; it must never be used as evidence that the learner completed CMU 17-803 or an official CMU assignment.

Grade repository artifacts and reproducible command output, not unsupported prose. Do not require any linked website, recording, unspecified reading, or non-open-source assignment. Those materials are outside this unit.

## Preconditions

Before scoring, verify that the submission contains `DESIGN.md`, `data/benchmark.csv`, `src/analyze.py`, automated tests, `artifacts/summary.json`, `REPORT.md`, `RUN.md`, and `COMPREHENSION_RESPONSES.md`.

Return the submission for correction without awarding a pass if any of these integrity conditions occurs:

- the submission represents this work as official CMU material or whole-course completion;
- results are hard-coded rather than derived from the input;
- invalid or missing records are silently discarded, repaired, or imputed;
- fabricated measurements, inferential results, provenance, or restricted materials are presented as evidence;
- the documented test or analysis command cannot run in the declared supported environment.

## Scoring (100 points)

### A. Empirical design — 20 points

- 4: The research question is precise and limited to the supplied observations.
- 4: Directional and null statements are coherent and operationalized.
- 5: Observational unit, pairing, explanatory variable, outcome, and median paired-percent-change estimand are correctly distinguished.
- 3: The desired target population is separated explicitly from the observed sample.
- 4: At least four relevant threats are explained, including measurement and sampling/generalization threats; the proposed rerun protocol addresses environment, warm-up, repetitions, order, and version identity.

### B. Data contract and defensive behavior — 15 points

- 4: The CSV is transcribed faithfully with 16 rows, eight case IDs, and the required fields.
- 7: All specified schema, type, domain, uniqueness, matching-covariate, and complete-pair checks are implemented.
- 4: Invalid inputs fail clearly on standard error with nonzero status and do not yield a misleading partial result.

### C. Analysis correctness — 25 points

- 8: Pair construction and the percent-change formula are correct, with baseline as denominator and full internal precision.
- 7: Pair counts, per-pair results, overall median, and family medians are correct.
- 4: Output implements the requested logical schema, ordering, two-decimal serialization, empty exclusions, and input SHA-256.
- 6: The result is genuinely computed from arbitrary valid input rather than keyed to the supplied IDs or expected constants.

Reference values for the supplied CSV, rounded only at serialization:

| Quantity | Expected value |
|---|---:|
| Rows | 16 |
| Matched pairs | 8 |
| Sparse-family median percent change | -20.00 |
| Dense-family median percent change | 6.83 |
| Overall median percent change | -7.34 |

Expected per-pair percent changes are: `sparse-1000-11` -20.00, `sparse-1000-29` -20.45, `sparse-5000-11` -20.00, `sparse-5000-29` -20.00, `dense-1000-11` 6.67, `dense-1000-29` 5.32, `dense-5000-11` 7.92, and `dense-5000-29` 7.00.

### D. Software engineering and reproducibility — 20 points

- 5: The CLI honors explicit input/output paths, creates the output directory, and avoids environment-specific paths or state.
- 5: JSON output is deterministic across unchanged runs: sorted records and keys, stable formatting, no live timestamp, and trailing newline.
- 7: Automated tests cover the valid case, reordered rows, missing partner, duplicate implementation, and malformed/non-positive runtime; tests are isolated with temporary paths.
- 3: `RUN.md` accurately records environment, exact commands, artifact roles, synthetic provenance, and lack of external dependencies.

The examiner should run, from the submission root:

```bash
python3 -m unittest discover -s tests -v
python3 src/analyze.py --input data/benchmark.csv --output artifacts/summary.json
```

Then hash or compare two independently regenerated summaries from unchanged input. Also mutate one valid runtime and confirm the corresponding result changes, and remove one partner row and confirm failure.

### E. Interpretation and claim discipline — 12 points

- 4: `REPORT.md` states the computed overall and family-specific observations accurately.
- 3: It foregrounds the reversal in direction between sparse and dense families rather than relying on the aggregate alone.
- 3: Its positive claim is descriptive and limited to the eight observed pairs; it separately rejects causal, cross-input, cross-machine, and repeated-run generalization.
- 2: Follow-up improvements are concrete and connected to identified threats; no unobserved statistics or experimental details are invented.

### F. Comprehension — 8 points

Award one point for each response that directly answers its prompt with correct, scenario-specific reasoning. Look for these essential ideas:

1. The comparison unit is a matched `case_id`; implementation rows within a case are dependent components of one contrast.
2. Paired percent change preserves within-case relative direction/magnitude with baseline denominator; a valid alternative summary must be identified with its different target question.
3. Report aggregate and strata, emphasize heterogeneity, and avoid a universal implementation choice based only on the aggregate.
4. Invalid structure changes or destroys the empirical comparison; the example must connect a concrete validation to a misleading result it prevents.
5. Stable computation and rerunnable artifacts are demonstrable; repeatability of measured runtimes requires new controlled executions.
6. A causal claim needs controlled assignment/order and nuisance-factor control; a population claim needs broader, justified sampling and replication.
7. A normalized link record is discovery metadata until access, provenance, role, offering, and official status are verified.
8. The proposed protocol change must be feasible, specific, and tied to a named measurement threat.

## Decision

- **Pass:** at least 75/100, at least 13/25 in Analysis Correctness, at least 10/20 in Software Engineering and Reproducibility, and no integrity-condition failure.
- **Revise:** below a threshold or missing required evidence. Record the failed checks and preserve the attempt for comparison after revision.

Do not translate a Pass into whole-course completion. Promotion of the unit result remains the responsibility of the harness-controlled validator.
