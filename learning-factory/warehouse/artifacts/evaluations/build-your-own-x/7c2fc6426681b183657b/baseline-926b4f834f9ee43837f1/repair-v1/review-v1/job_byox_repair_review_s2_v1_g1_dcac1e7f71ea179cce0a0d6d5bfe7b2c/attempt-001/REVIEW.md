# Independent review

## Verdict: REVISE

The pack is well structured and unusually candid about its validation boundary, but its sealed
reference violates the published token/name contract. The defect is localized; it should be fixed
and covered before the reference is treated as an educational oracle. This verdict is advisory and
does not award `REVIEWED` or any other validation label.

## Prioritized finding

### P1 — An overflowing decimal prefix incorrectly poisons a nonnumeric word name

`REQUIREMENTS.md:17-21` allows a 1–31 byte user name unless the *complete token* has integer shape.
Both `9223372036854775808x` (20 bytes) and `-9223372036854775809x` (21 bytes) are therefore valid
names: their final `x` means neither token is an integer.

The reference instead rejects both definitions:

```text
: 9223372036854775808x 7 ; 9223372036854775808x .
    => status 2, stdout empty, stderr "error: invalid definition\n"

: -9223372036854775809x 8 ; -9223372036854775809x .
    => status 2, stdout empty, stderr "error: invalid definition\n"
```

The cause is in `sealed/reference/forth.S:447-479`: `parse_number` returns its overflow state as soon
as the accumulated prefix exceeds `int64`, without first confirming that all remaining bytes are
digits. `begin_definition` then rejects every nonzero parser state at lines 551–555. This also makes
the claim in `sealed/REVIEW.md:8` too broad and leaves the sealed oracle unable to distinguish an
overflowing digit string from a word whose early digits happen to overflow.

Fix the lexical classification before the range classification. A simple repair is to validate the
entire optional-minus-plus-digits shape first, or to continue scanning after arithmetic overflow and
return “not numeric” if any later byte is nondigit. Add positive and negative overflow-prefix suffix
cases to `sealed/reference_tests/test_reference.py`; the two definitions above should print `7\n`
and `8\n` respectively.

## Evidence that held up

- The reference built reproducibly at three source/output locations. All copies had SHA-256
  `5b73caee22ee3e317b10049367130fcfb23a4973bff821c38f928cf2b9218e98`.
- The ELF is a static x86-64 `ET_EXEC` with `_start`, no dynamic section, and a non-executable GNU
  stack. No scratch or workspace path was found in its strings.
- Public tests passed 10/10, sealed tests 13/13, and tooling/audit regressions 6/6 with no skips. A
  reviewer-designed program also matched 880 independently calculated arithmetic results.
- The starter builds and deliberately returns status 2 with only
  `error: interpreter not implemented\n` on stderr, consistent with the documented partial state.
- The manifest makes no promotion claim: it remains `GENERATED`/`PARTIAL`, requires independent
  validation, and says `productionized: false`. Benchmark output is labeled
  `UNVALIDATED_MEASUREMENT`.
- The learner surface is useful and progressively staged: the contract, concepts, design questions,
  starter, and public examples are nonsealed, while implementations and exercise answers are under
  `sealed/`.
- The license boundary correctly separates CC0 catalog metadata from the linked resource whose
  license is `NOASSERTION`; it does not assert that CC0 covers Jonesforth.

## Limitations and nonblocking observations

- QEMU execution with the configured GLib path produced mixed results at the recorded three-second
  bound: two cold/non-strace attempts timed out and later attempts passed. This is insufficient for
  transfer verification; a longer cold-start allowance and repeated runs would make the smoke check
  more reproducible.
- The upstream snapshot and linked source were not available, so their hashes, license evidence,
  similarity, and the clean-room assertion could not be authenticated. The generated material is
  described as for personal educational use but has no separate redistribution license.
- All evaluator material is correctly grouped under `sealed/`, but actual exclusion from a learner
  view depends on the external control plane and was not testable here.
- No fuzzing, coverage run, validated benchmark, production assessment, or broader platform matrix
  was performed. The candidate does not claim otherwise.

