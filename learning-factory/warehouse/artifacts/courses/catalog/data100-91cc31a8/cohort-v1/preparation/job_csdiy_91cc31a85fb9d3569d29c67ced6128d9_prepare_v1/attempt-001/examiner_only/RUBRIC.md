# Independent Rubric: Reproducible Data Audit Kickoff

Artifact provenance: manager-authored from the supplied CSDIY catalog snapshot and the synthetic fixture in the learner task; no external course content was retrieved.

Validation label: `EXAMINER_ONLY_EVALUATION_SPECIFICATION_UNVALIDATED` — use this only for independent harness/examiner evaluation. It is not itself evidence of learner completion.

## Scope and decision rule

Score only the bounded local kickoff. Do not award or infer completion of Data100. Inspect the submitted files, run tests in an isolated copy, and generate fresh output; a learner's prose claim or committed report alone is not evidence.

The unit passes at 80/100 only if all three gates also hold:

1. the implementation runs using only the Python 3 standard library;
2. it preserves all structurally valid input rows and does not hard-code the supplied fixture's result; and
3. expected operational failures cannot replace an existing output file.

If a gate fails, record the numeric score but mark the unit unsuccessful. Only the harness-controlled validator may promote job state.

## Reference observations for the supplied fixture

Use these as examiner oracles; they must not be copied into learner-visible files.

- There are 6 physical data rows on source lines 2 through 7.
- Four rows have no row-level errors and two have row-level errors. Repetition of an identifier does not change those validity counts.
- `duplicate_ids` is exactly `["r2"]`; both `r2` rows remain in source order.
- The row on line 4 has a missing score, normalized to `null`, with no score error.
- The row on line 5 has a nonempty invalid score, normalized to `null`, with the score error `invalid_number`.
- The row on line 6 has a missing city and the city error `required`.
- Score statistics are `missing: 1` and `invalid: 1`; city `missing: 1`; row ID `missing: 0`; active `invalid: 0`.
- The cleaned city values from `Chicago`, ` chicago `, and `Chicago` retain their cleaned spellings, while all three city keys compare as `chicago`.
- Case-insensitive Boolean parsing makes `TRUE` valid. All other fixture Boolean values are also valid.
- The report's SHA-256 must equal a fresh digest of the exact submitted fixture bytes. Numeric JSON values `10` and `10.0` are semantically equivalent for scoring.

## Scoring

### 1. Contract-correct transformation — 35 points

- 8 points: exact header/shape handling, UTF-8 reading, physical source-line tracking, and preservation of every raw row.
- 9 points: correct trimming, whitespace collapse, city key, finite numeric parsing, Boolean parsing, and JSON types.
- 8 points: correct missing-versus-invalid treatment and exact structured row errors.
- 5 points: duplicate detection is generic, deterministic, dataset-level, and non-destructive.
- 5 points: summaries and field statistics match independently recomputed values and their invariants.

Deduct all points for a subpart whose result is fixture-hard-coded rather than derived. Minor representational deviations earn credit only when they do not contradict the published schema.

### 2. Deterministic artifact and operational safety — 20 points

- 5 points: output follows the required schema, source order, error order, duplicate order, formatting, and final-newline rules.
- 4 points: input basename and fresh byte-level SHA-256 are correct; no absolute path or ungrounded provenance claim appears.
- 4 points: unchanged successful runs are byte-identical and contain no time-, host-, locale-, or randomness-dependent fields.
- 4 points: same-directory temporary write, close/flush before `os.replace`, and cleanup are correctly implemented.
- 3 points: expected usage, decoding, CSV, shape, and I/O failures return 2 with concise stderr diagnostics and no traceback.

Award no atomic-safety points if the target is opened or removed before the full replacement file is ready.

### 3. Software design and clarity — 15 points

- 6 points: parsing, normalization/validation, aggregation, serialization, and CLI concerns have testable boundaries without unnecessary framework code.
- 3 points: import has no side effects; reusable logic does not print or exit; CLI logic is narrow.
- 3 points: names, types or docstrings, and error representation make the contract legible.
- 3 points: `DECISIONS.md` accurately describes choices and assumptions, including why duplicates are preserved.

### 4. Learner tests — 15 points

- 4 points: an end-to-end fixture test checks content rather than only process success or file existence.
- 4 points: focused tests distinguish missing/invalid values and cover normalization, duplicates, and provenance lines.
- 4 points: failure tests cover header/shape behavior and prove a sentinel output remains byte-for-byte unchanged.
- 3 points: a repeated-run test compares output bytes; tests use temporary directories and are order-independent.

Examiner-added tests, not the learner suite alone, determine correctness.

### 5. Comprehension and complexity — 15 points

Evaluate explanations for the following substantive ideas:

- 2 points: missing means absent but permitted, whereas invalid means present but outside the type contract; retaining error metadata prevents silent conflation.
- 2 points: preserving duplicates avoids arbitrary data loss and keeps policy separate from observation.
- 2 points: determinism discussion identifies at least four credible factors such as timestamps, paths, set/dict-derived ordering, locale, random values, float special values, or platform newlines.
- 2 points: the normalization property is general and falsifiable; for example, idempotence or equivalence under surrounding/collapsible whitespace and casing at the key level.
- 3 points: complexity is justified from the implementation. A conventional solution is linear in total input/output size, with linear retained space because the required report includes every record; sorting distinct duplicate IDs or errors must be accounted for if non-constant.
- 2 points: invariants include every row appearing exactly once, `total = valid + invalid`, and field counters agreeing with record states.
- 1 point: a digest identifies exact bytes but does not prove correctness, authorship, safety, or truth.
- 1 point: later course expansion requires authorized retrieval evidence, stable identity/provenance, availability and license checks, official-unit evidence, ordering evidence, and revalidation; a link alone is insufficient.

## Integrity caps and reporting

- Cap at 50 if the program emits a precomputed fixture result or otherwise cannot handle a second conforming CSV.
- Cap at 60 for silent row dropping, implicit duplicate winner selection, or conflating missing and invalid score values.
- Cap at 70 if required tests are absent or cannot be discovered by the published command.
- Mark unsuccessful regardless of score if learner-visible files contain this rubric or reference answers.

Report category scores, gate results, commands run, observed exit codes, and hashes of evaluated artifacts. Preserve failure logs as evidence.
