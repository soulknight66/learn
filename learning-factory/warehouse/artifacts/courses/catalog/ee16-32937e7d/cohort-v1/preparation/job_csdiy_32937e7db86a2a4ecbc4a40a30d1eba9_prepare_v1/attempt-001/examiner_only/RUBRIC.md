# Independent examiner rubric: kickoff unit 001

This file is examiner-only. Do not copy scoring rules, expected responses, or diagnostic fixtures into learner-visible artifacts.

## Scope and evidence

Evaluate only **From ADC Counts to a Tested Sensor Pipeline**. A passing result is evidence for this kickoff unit only. It is never evidence of completion of EE16A, EE16B, or the catalog course.

Run the learner’s documented commands in a clean Python 3.11 environment with external network access disabled. Preserve command lines, exit codes, stdout/stderr, test logs, inspected output bytes, and any independently generated fixtures as validation evidence. A learner’s prose claim earns no behavioral credit without corresponding code or evidence.

The examiner may inspect but must not modify the submission before scoring. Harness-controlled tests should use temporary directories and must not expose their fixtures or this rubric to the learner submission.

## Scoring summary

Score out of 100:

| Area | Points |
|---|---:|
| Circuit model and numeric behavior | 16 |
| Parsing and validation contracts | 14 |
| Rolling-median transformation | 14 |
| CLI and failure-safe publication | 14 |
| Automated tests | 18 |
| Design and operational documentation | 10 |
| Comprehension responses | 14 |

Do not award the same behavior twice. Partial credit requires inspectable evidence.

## 1. Circuit model and numeric behavior — 16 points

- **4:** Correctly derives and implements `R_s = R_f * V_node / (V_ref - V_node)` for the stated topology.
- **3:** Uses `V_node = (c / M) * V_ref` with configuration values rather than hidden constants.
- **3:** Accepts zero count as zero volts/zero ohms and handles near-saturation with finite calculations; rejects `c == M` and all other invalid counts rather than clamping.
- **2:** Validates finite positive `V_ref` and `R_f` and integer `M >= 2`.
- **2:** Carries full calculation precision and applies fixed six-place formatting only at serialization.
- **2:** Keeps model arithmetic callable independently of CLI and CSV concerns.

Useful independent fixtures with defaults include counts `0`, `1`, values on either side of half scale, and `4094`. Calculate oracle values from rational/decimal arithmetic in the harness rather than copying learner code.

## 2. Parsing and validation contracts — 14 points

- **3:** Requires the exact two-column header and at least one data row.
- **3:** Rejects bad row shapes, blank records, and non-integer data without silently skipping.
- **3:** Enforces nonnegative, strictly increasing timestamps across the full input.
- **2:** Reports a correct one-based file line for data errors and emits no traceback for expected failures.
- **3:** Validates the complete input before output publication and does not clamp, sort, or deduplicate.

Test a failure in the final record, not just the first, to catch streaming implementations that have already published partial output.

## 3. Rolling-median transformation — 14 points

- **3:** Enforces a positive odd window and respects the configured value.
- **4:** Produces the required trailing median for startup prefixes, full windows, and after old elements leave.
- **2:** Uses the arithmetic mean of the two middle values for even startup prefixes.
- **2:** Handles duplicate values and isolated outliers correctly while preserving record order.
- **2:** States a valid invariant and accurate time/space complexity for the implementation actually submitted.
- **1:** Median logic is independently testable and does not mutate caller-owned observations unexpectedly.

An acceptable invariant is that immediately before each median is emitted, the maintained multiset contains exactly the raw resistance values at indices `max(0, i-N+1)` through `i`, with multiplicity. Complexity may legitimately be `O(nN log N)` for re-sorting each bounded window, `O(nN)` with a sorted-list update, or `O(n log N)` with a correctly engineered balanced/two-heap structure; accuracy of the claim matters more than choosing the cleverest structure.

## 4. CLI and failure-safe publication — 14 points

- **2:** Implements the specified module invocation, arguments, defaults, and nonzero error exits.
- **3:** Produces the exact header, input order, integer fields, fixed six-place floats, UTF-8 encoding, and `\n` line endings.
- **2:** Rejects input/output identity, including aliases that the implementation can reasonably resolve.
- **4:** Writes a temporary file in the destination directory and atomically replaces the destination only after all processing and serialization succeed.
- **2:** Preserves an existing destination byte-for-byte on invalid input or a simulated pre-replace write failure, and cleans temporary artifacts.
- **1:** Expected errors are concise and directed to stderr; successful operation is automation-friendly.

Merely opening the final output with mode `w` after validation earns at most 1 of the 4 atomic-replacement points: it still risks truncation on a write, encoding, disk, or process failure.

## 5. Automated tests — 18 points

- **4:** Model tests use independently reasoned expected values and cover ordinary and boundary counts.
- **4:** Parser/validation tests cover header, shape, type, timestamp, range, and configuration failures.
- **4:** Median tests cover startup, eviction, duplicates, outlier behavior, and at least one non-default window.
- **3:** CLI integration checks exact serialized bytes and exit behavior.
- **3:** A test begins with known destination bytes, supplies invalid late input, and proves those exact bytes remain.

Tests that merely duplicate implementation formulas without an independent oracle, contain no meaningful assertions, depend on execution order, or require network access receive no credit for the affected item.

## 6. Design and operational documentation — 10 points

- **2:** README commands work as written from the submission root in the stated environment.
- **2:** DESIGN accurately explains topology, units, inverse algebra, and the saturated boundary.
- **2:** Documents validation/error categories and separation between model, transformation, I/O, and CLI.
- **2:** Documents median invariant/complexity and the actual atomic-publication sequence.
- **2:** States numeric choices, test strategy, and limitations without claiming physical calibration or official-course equivalence.

## 7. Comprehension responses — 14 points

Award 0, 1, or 2 points for each of questions 1–7. Question 8 is scored within the final item below, so the seven items are:

1. **Inverse and domain:** full credit for valid algebra, `V_ref - V_node` denominator, domain `0 <= V_node < V_ref` under this task’s accepted counts, and consistent ohm units.
2. **Saturation:** full credit for explaining denominator collapse/unbounded sensitivity, why a finite sentinel is misleading, and a test that asserts rejection/no output at `c == M`.
3. **Filtering limits:** full credit for two distinct persistent causes such as wrong topology, resistor tolerance, reference bias, systematic ADC error, or sensor self-heating, linked to why a median cannot correct bias/model mismatch.
4. **Median invariant/counterexample:** full credit for a multiplicity-aware trailing-window invariant and a concrete stream where cumulative and evicting-window medians diverge at a named step.
5. **Atomicity:** full credit for validation before temp creation (or safe cleanup), temp write/flush-close, atomic replace only on success, and a byte-preservation test. Requiring `fsync` is not part of this unit.
6. **Test roles:** full credit for three concrete tests correctly distinguished as boundary, broad property, and integration behavior.
7. **Evidence boundary plus transfer (questions 7 and 8 together):** full credit requires both (a) preserving that the catalog claims an official aggregate assignment pointer while declining to infer assignment bodies/order/dependencies, with retrieval, provenance, license/access, granularity, and solution-boundary verification named; and (b) recognizing that reversing topology changes model equations/expected numeric fixtures but should leave parser, CLI, atomic writer, and preferably generic filter stable.

If question 8 is absent, item 7 can earn at most 1 point. Concise correct reasoning is sufficient; reward understanding, not length.

## Result bands and caps

- **SUCCEEDED candidate:** 75–100, no critical cap, learner tests pass, and harness contract checks pass.
- **REVISION REQUIRED:** 50–74, or a score otherwise passing but limited by a cap.
- **NOT YET DEMONSTRATED:** 0–49.

Apply these caps after totaling:

- No runnable implementation or behavior is substantially hard-coded to a single fixture: cap at 49.
- No automated tests, or tests cannot be discovered by the documented command: cap at 64.
- Existing output is modified on an invalid-input harness case: cap at 69.
- Saturated input is silently clamped/accepted, or malformed rows are silently dropped: cap at 69.
- Required comprehension responses are absent: cap at 74.
- Submission requires network access or unrecorded external course content: cap at 74.

The examiner records the numeric score, applicable caps, failed commands, and evidence paths. Only the harness-controlled validator—not this rubric or examiner prose—may promote job state.
