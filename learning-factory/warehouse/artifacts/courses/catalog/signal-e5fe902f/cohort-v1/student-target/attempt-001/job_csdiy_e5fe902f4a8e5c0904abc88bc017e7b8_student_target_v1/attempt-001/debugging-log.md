# Debugging Log

This log records concise engineering hypotheses, experiments, observed
failures, corrections, and lessons. It does not contain private reasoning.

## 1. Contract boundary and representation

**Hypothesis:** Copying the sample iterable to floats, storing a tuple, and
blocking attribute writes will prevent mutable aliases while preserving
represented zeros.

**Experiment:** Added construction from a list, mutated the source list, tried
attribute and tuple-item assignment, and tested empty versus represented-zero
signals.

**Outcome:** The focused cases pass. The original list no longer aliases the
stored samples, mutation attempts raise, empty signals canonicalize, and
represented zeros retain their length and start.

**Lesson:** Immutability requires both defensive copying and a read-only public
surface; a tuple alone does not address an aliased mutable input before
conversion.

## 2. First full test run: runtime compatibility failure

**Hypothesis:** A frozen dataclass with postponed annotations would provide a
compact immutable value implementation.

**Experiment:** Ran the required command:

```text
python3 -m unittest discover -s submission -p 'test_*.py' -v
```

**Failure:** Test discovery stopped before running tests with
`SyntaxError: future feature annotations is not defined`. The local `python3`
reports version 3.6.8; postponed annotations and the standard-library
`dataclasses` module are later Python features.

**Correction:** Replaced the dataclass with a Python-3.6-compatible value class
using slots, read-only properties, guarded assignment/deletion, explicit value
equality/hash/repr, and `typing` forms supported by that runtime. Removed the
unsupported future import from tests.

**Verification:** Re-ran the same command. All 20 test methods passed in the
recorded run.

**Lesson:** “Python 3 standard library” does not imply the newest Python 3.
Executing the exact reproduction command early exposed an environmental
assumption that code inspection alone would not.

## 3. Correlated-correctness risk

**Hypothesis:** Direct/sparse agreement is useful but could allow a shared
start-index or output-length defect.

**Experiment:** Added two constant hand-derived convolution oracles, explicit
start/length assertions, and a two-input shift property whose expected start
is computed arithmetically rather than by reusing `shift`. Also ran 150
fixed-seed agreement cases split across empty, dense, and zero-heavy modes.

**Outcome:** All checks pass. This increases confidence but remains finite
evidence, not proof.

**Lesson:** Independence comes from varying the basis of evidence, not merely
duplicating an algorithm under a second function name.

## 4. Performance hypothesis

**Hypothesis:** Skipping exact-zero pairs should produce a large benefit on the
chosen zero-heavy case; dense behavior is uncertain because list construction
and loop structure also matter.

**Experiment:** Warmed up both algorithms, verified outputs, alternated call
order, and recorded seven raw repetitions for identical objects. Inputs were
dense 180-by-160 and zero-heavy 650-by-550 with 32 and 28 nonzeros.

**Outcome:** Dense medians were 2,331,090 ns direct and 2,193,511 ns sparse.
Zero-heavy medians were 32,281,356 ns direct and 546,704 ns sparse. No timing
samples were discarded. Python 3.6 required a documented conversion of
`perf_counter()` readings to integer nanoseconds.

**Lesson:** The zero-heavy result matches the operation-count hypothesis for
this case. The small dense sparse advantage was not assumed and is too narrow
to generalize; a size/density sweep is needed to discuss crossover behavior.
