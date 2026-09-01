# Comprehension Responses

1. After creation and every successful update, each counter is the number of
   accepted occurrences of its byte, `total` is the number of all accepted
   occurrences, and the mathematical sum of all 256 counters equals `total`
   without unsigned wrap. The invariants hold after initialization, after each
   `bytehist_add`, at every `fread` boundary, after successful EOF and owned-file
   close, and throughout reporting. `src/bytehist.c` checks both additions
   before either mutation, so a rejected update also leaves the prior invariant
   state intact.

2. `read_input` in `src/main.c` reads into an `unsigned char` array, and passes
   each element as an `unsigned char` to `bytehist_add`. It therefore represents
   every input byte as a value in 0 through 255 before selecting a counter. A
   signed `char` could turn `80` through `FF` into negative values on this
   platform, risking an invalid index, memory corruption, or incorrectly
   labelled/counting high bytes. The fixed high-byte case in
   `test_binary_file_includes_high_bytes` exercises this choice.

3. In `read_input` (`src/main.c`), any positive `fread` result is progress and
   all returned bytes are added. The function then checks `ferror` first and
   returns `READ_STREAM_ERROR`, checks `feof` and returns `READ_OK`, otherwise
   continues even if the read was short. A zero result with neither flag is a
   no-progress error. `main` emits a report only for `READ_OK` followed by a
   successful owned-file close; errors instead produce status 1 and a
   `bytehist:` diagnostic with standard output still empty.

4. Read boundaries do not affect the report because the input loop submits each
   byte exactly once in sequence, while each update adds one to only that byte's
   counter and the total. Regrouping the calls does not change those sums. The
   `test_lengths_around_two_processing_boundaries` cases use lengths 4095,
   4097, 8191, and 8193, supporting the claim on both sides of the 4096- and
   8192-byte boundaries. They do not directly establish behavior at exactly
   4096 or 8192 bytes.

5. `main` begins `emit_report` only after the complete read reports EOF without
   error and, for a named file, `fclose` succeeds. Thus another program that
   observes status 1 after an input failure also receives no bytes on standard
   output and cannot mistake a partial histogram for a completed report. It
   cannot infer that zero bytes were internally read—only that no report was
   accepted for emission. The unavailable and non-regular input tests assert
   the empty-output property.

6. `bytehist_add` rejects an occurrence count greater than either
   `UINT64_MAX - total` or `UINT64_MAX - selected_count`, and performs both
   checks before mutation. `read_input` maps rejection to a count-overflow
   failure, so no report is emitted and status is 1. Ignoring overflow could
   wrap the total or a counter to a small number (possibly zero), falsely
   claiming fewer bytes or even omitting a byte value that occurred. The C
   module test reaches the limit in one bulk update and verifies that two
   rejected updates do not mutate state.

7. `test_binary_file_includes_high_bytes` has a six-byte literal input and a
   separately written literal expected report. The oracle is a reviewed fixed
   byte string, not a call to the production module or a reimplementation of
   its loop. It would miss a defect that appears only when the stream crosses a
   processing-chunk boundary; the separate boundary test addresses that class.

8. I would retain the opaque `ByteHistogram`, its checked update and observer
   interface, and the `read_input` loop because none has presentation policy.
   I would replace or extend `emit_report` and add a narrowly scoped format
   selection responsibility in the CLI. The current boundary in
   `include/bytehist.h` keeps formatting, arguments, streams, and diagnostics
   out of the counting module, so a second formatter need not alter its state or
   invariants.

9. Trace for the “bytes at and above `80`” requirement: `DESIGN.md` specifies an
   unsigned input representation; `read_input` in `src/main.c` uses an
   `unsigned char` buffer and `bytehist_add`; the Python test
   `test_binary_file_includes_high_bytes` fixes counts for `80` and `FF`; and
   `TEST_REPORT.md` records that the black-box suite passed. That trace has no
   known gap in the ordinary build. Broader remaining gaps are that an owned
   input's `fclose` failure was not injected and the attempted UBSan run could
   not link in this environment.

---

Provenance: learner-authored solely from `COURSE_BRIEF.md`, `STUDY_TASK.md`,
`COMPREHENSION.md`, and local experiment results.

Validation label: `LEARNER_SELF_REVIEWED_AWAITING_INDEPENDENT_VALIDATION`.
