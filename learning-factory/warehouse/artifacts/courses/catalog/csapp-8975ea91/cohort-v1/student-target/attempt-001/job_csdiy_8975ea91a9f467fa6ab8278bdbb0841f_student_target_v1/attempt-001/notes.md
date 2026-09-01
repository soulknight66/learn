# Learner Notes: Kickoff Unit 1

## Scope guard

This work covers only the manager-authored “Trustworthy Byte Histogram” kickoff
unit. I did not retrieve the textbook, course site, recordings, official labs,
solutions, or any later unit. The broader course remains incomplete and
unassessed.

## Contract-to-design notes

- The histogram is an opaque owned object. Its module is responsible for
  allocation, mutation, invariants, and overflow checks; the CLI owns argument
  handling, streams, diagnostics, formatting, and exit status.
- Reporting is deliberately delayed until successful EOF and successful close
  of an owned input. This converts “input failure leaves stdout empty” from a
  cleanup hope into a control-flow property.
- Input bytes live in an `unsigned char` buffer. The key risk being controlled
  is sign extension or a negative array index for `80` through `FF`.
- The update API accepts an occurrence count even though the CLI adds one byte
  at a time. That makes an otherwise unreachable `UINT64_MAX` boundary
  deterministic to unit-test without weakening the normal input path.
- Output calls and the final flush are checked. On systems defining `SIGPIPE`,
  the signal is ignored so a closed pipe becomes an observable stdio error and
  status 1 rather than an unclassified signal termination.

## Concrete hypotheses and experiments

| Hypothesis | Experiment | Observation |
| --- | --- | --- |
| An unsigned byte path preserves `80` and `FF`. | Named-file test containing `00 0A 7F 80 FF 80`. | Exact fixed report passed, including `80 2` and `FF 1`. |
| No report is emitted for input failure. | Missing path and a directory used as an input name. | Both returned status 1, a `bytehist:` diagnostic, and empty stdout. |
| Counts do not depend on 4096-byte read boundaries. | Repeated-byte inputs of 4095, 4097, 8191, and 8193 bytes. | Every exact total and counter passed. |
| A broken consumer is an output failure, not success. | Child stdout connected to a pipe with no read endpoint. | Program returned 1 and emitted `bytehist: output failed`. |
| Overflow rejection can be atomic. | Module update to `UINT64_MAX`, followed by two one-count attempts. | Both attempts failed and total/counters retained their prior values. |
| A UBSan build might add runtime evidence. | Rebuilt with `-fsanitize=undefined`. | Object compilation succeeded; link failed because the local UBSan runtime was missing. No sanitizer result was claimed. |

## Lessons

The algorithm was the easy part. The useful systems practice was deciding when
output becomes trustworthy, treating cleanup as a possible failure, ensuring
stdio's signal behavior does not bypass the exit-status contract, and designing
an interface whose extreme state can be tested without creating an enormous
file. Fixed expected reports also made formatting and ordering failures visible
without sharing logic with the implementation.

## Deliberately deferred

Compression, Unicode interpretation, multiple-file aggregation, concurrency,
networking, assembly, alternate output formats, and later course labs are
future work, not part of this attempt.

---

Provenance: learner-authored from the three supplied learner-safe files and the
local experiments documented above.

Validation label: `LEARNER_NOTES_ONLY_NOT_COMPLETION_EVIDENCE`.
