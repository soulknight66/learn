# Examiner-Only Rubric: Empirical Entropy Kickoff

> Provenance: independently authored evaluation specification for `kickoff_01_empirical_entropy`; it is not an MIT rubric.
>
> Validation label: `EXAMINER_ONLY_EVALUATION_SPEC`. Keep this file outside every learner-visible bundle.

## Evaluation boundary

Score only the bounded kickoff artifacts under `submission/`. Do not award credit for an assertion that something passed; inspect the code, run deterministic checks, and preserve command output as evidence. Do not require any external textbook, website, Matlab file, or network access. Unit success never implies course success.

Use Python 3.11 and a clean temporary directory. At minimum, run:

```bash
python3 -m unittest discover -s submission -p 'test*.py' -v
python3 submission/entropy_tool.py EXAMINER_CREATED_NONEMPTY_FIXTURE
```

Import `entropy_from_counts` directly for evaluator-owned cases. Create fixtures locally, including an empty file, repeated bytes, all 256 byte values, invalid UTF-8 bytes, and a file larger than the implementation's stated chunk size. Capture exit status, stdout, and stderr separately. Never modify the learner's source to make it pass.

## Hard gates

The unit cannot pass, regardless of points, if any of these applies:

- one or more of the four required submission artifacts is missing;
- the evaluator cannot import the module or execute the documented CLI in Python 3.11;
- the reported entropy is fabricated, constant, or not derived from the entire target file;
- successful analysis requires network access or unavailable/restricted course content;
- expected user errors expose secrets or examiner-only material; or
- the total score is below 70/100.

A hard-gate failure is durable failed-attempt evidence, not permission to mark the unit or course complete.

## Scored criteria (100 points)

### 1. Artifact and interface integrity — 8 points

- **3:** exactly the required source, learner tests, README, and response document are present and inspectable; scratch products do not substitute for them.
- **3:** `entropy_from_counts` is importable without running the CLI or producing output as an import side effect.
- **2:** the documented invocation works from the repository root using the specified paths.

### 2. Entropy calculation and contract — 24 points

- **12:** correct base-2 results within a reasonable floating tolerance for evaluator cases: `[7] -> 0`, `[1, 1] -> 1`, `[1, 1, 1, 1] -> 2`, `[1, 1, 2] -> 1.5`, and `[9, 3, 0, 0] -> 0.8112781244591328...` bits per symbol.
- **4:** zero-count entries are skipped safely when at least one count is positive.
- **4:** a one-shot iterable is consumed no more than once, with no assumption that `len` or indexing is available.
- **4:** results remain invariant under permutation and common positive scaling of counts.

### 3. Validation and failure semantics — 12 points

- **6:** negative counts and all-zero/empty iterables raise `ValueError`; boolean and other non-integer counts raise `TypeError`; malformed inputs are not silently repaired.
- **6:** missing/extra CLI arguments, missing or unreadable targets, directories, and empty files return nonzero, put a concise diagnostic on stderr, put no success JSON on stdout, and suppress tracebacks for expected user errors.

### 4. Binary streaming and CLI result — 20 points

- **6:** analysis is binary and counts nulls, newlines, `0xff`, and other non-text bytes without decoding.
- **6:** the entire input is processed across chunk boundaries, and a fixture larger than one chunk agrees with an independently computed reference count.
- **4:** inspection plus an evaluator-owned large fixture supports bounded reading and auxiliary space independent of file length; the implementation does not retain all chunks or call an unbounded `read()`.
- **4:** success emits one parseable JSON object and status 0; keys are exactly `byte_count`, `distinct_byte_values`, and `entropy_bits_per_byte`, with integer count values and a finite numeric entropy.

### 5. Learner-owned tests — 14 points

- **6:** tests exercise the required known distributions, mixed zeros, permutation, scaling, and invalid count types/values with meaningful assertions.
- **5:** temporary binary fixtures cover empty input, non-UTF-8 bytes, more than one chunk, success JSON, and at least two CLI failures.
- **3:** tests are deterministic, isolated, network-free, use an explicit floating tolerance, and pass under the documented discovery command.

### 6. Engineering documentation — 7 points

- **3:** README accurately states the input/error contract, byte model, chunking decision, and exact run/test commands.
- **2:** complexity is stated as `O(n + a)` time and `O(a + b)` auxiliary space, or an equivalent precise formulation, where `n` is file length, `a = 256` is alphabet size, and `b` is the bounded chunk size; it may simplify these to linear time and constant space with the fixed parameters explained.
- **2:** at least one genuine limitation is named, such as ignored symbol dependence, model granularity, coding overhead, or the difference between observed and source distributions.

### 7. Comprehension — 15 points

Score the eight numbered responses using the key below. Award **2 points each for questions 1–7** and **1 point for question 8**. A response earns its points only when the conclusion and supporting reasoning are both present.

1. Probabilities are `0.75`, `0.25`, `0`, `0`; the positive terms give approximately `0.8113` bits per observed symbol. Zero terms are omitted under the zero-log-zero convention.
2. Omitting individual zero terms is valid when total count is positive. An all-zero collection has total zero, defines no empirical distribution, and must raise `ValueError` under the assigned contract.
3. Both numerator and total scale by the same factor, so each probability and therefore entropy is unchanged. The cited test should compare scaled and unscaled valid vectors numerically.
4. Bytes give a total observation rule for arbitrary binary input. Invalid UTF-8, multibyte characters, or encoding/newline transformations are acceptable examples; evidence must exercise raw bytes and verify byte counts/results.
5. A fixture spanning multiple chunks with different distributions across chunks should match an independent whole-file reference; resetting would make the output depend only on a chunk. Boundary-adjacent sizes or alternate chunk sizes strengthen the test.
6. The response should distinguish function type errors, function value/domain errors, and CLI invocation/I/O/domain failures. Expected CLI failures are nonzero with no success JSON on stdout and a concise stderr diagnostic.
7. Entropy under a single-byte empirical model is not an exact compressor output because coding/model/container overhead and dependence matter. Cryptographic unpredictability additionally needs a threat model and justified source/conditional or min-entropy assumptions; empirical Shannon entropy alone is insufficient.
8. With file length `n`, fixed alphabet `a = 256`, and bounded buffer `b`, scanning is linear and storage is bounded by counters plus one buffer. Evidence should combine code inspection with a multi-chunk or large-file test; merely claiming streaming is insufficient.

## Decision record

- **Pass:** no hard gate fails, score is at least 70, evaluator-owned functional checks pass, and no unresolved critical contract defect remains.
- **Revise:** evidence is executable but the threshold or one critical criterion is unmet; record exact failing commands/cases for the durable attempt.
- **Invalid:** artifacts are inaccessible, rely on prohibited material, or cannot be evaluated safely; record the reason without inferring learner completion.

Record the numerical score, hard-gate outcomes, commands executed, exit statuses, and relevant output paths. Only the harness-controlled validation result may promote the unit state.
