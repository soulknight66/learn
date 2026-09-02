# Independent review

Verdict: **REVISE**.

The submission is a useful, unusually candid educational scaffold, and its
conservative `GENERATED` + `PARTIAL` metadata is appropriate. It is not ready
for an advisory PASS because independent checks reproduced three blocking
correctness/reproducibility defects and found gaps between advertised and
executable validation coverage.

## Prioritized findings

### P1 — Recovery silently erases a plausible length-prefix corruption

`CANDIDATE/REQUIREMENTS.md:19-22` requires decoding to distinguish an
incomplete final frame from a complete corrupt frame, and lines 32-34 allow
automatic truncation only for an incomplete final suffix. The reference CRC
covers the body but not the four-byte length. At
`CANDIDATE/sealed/reference/src/main/java/edu/learningfactory/minilog/RecordCodec.java:127-136`,
any plausible declared length larger than the remaining bytes becomes
`TORN_TAIL`; `SegmentedLog.java:97-104` then truncates it.

An independent probe wrote and forced one 41-byte frame, changed only its
length prefix from 37 to 38, and reopened it. The reference returned an empty
log after shrinking the segment from 41 bytes to 0; it did not raise
`CorruptLogException`. This is exactly the evidence-loss scenario R2/R3 say
must not happen. `CANDIDATE/sealed/DESIGN.md:12-18` acknowledges the ambiguity,
but the learner contract does not, while `sealed/REVIEW.md:16` still claims
that only a torn suffix is repaired.

Revise the format so length integrity can be checked independently (for
example, a fixed checksummed header or complemented length plus a body CRC),
then add a deterministic plausible-length-bit-flip regression. Narrowing the
contract instead would need equally explicit learner-facing disclosure and
must not retain the current evidence-preservation claim.

### P1 — The documented test commands do not run in the supplied workspace

Both exact commands in `CANDIDATE/VALIDATION.md` failed before `javac` ran.
`environment/run_public_tests.py:66` and `sealed/run_reference_tests.py:50`
call `tempfile.TemporaryDirectory` without a directory override. In this
read-only-candidate sandbox, Python reported no usable directory among
`/tmp`, `/var/tmp`, `/usr/tmp`, and `CANDIDATE`, returning exit 1.

This is especially material because `VALIDATION.md:56-60` says the sandbox's
default `/tmp` was known to be unavailable and says both runners were
corrected. Only the child JVM's `java.io.tmpdir` was corrected; Python must
first create the build directory. Supplying an unrecorded writable `TMPDIR`
made the claimed 1/5 and 5/5 + 11/11 results reproducible.

Add a documented `--temp-root` (including to the sealed runner), select a
known per-attempt writable location deterministically, or record and validate
the required `TMPDIR`. The documented command must work without an implicit
environment precondition.

### P1 — Segment names depend on the host locale and cannot always be reopened

Discovery accepts only ASCII digits via `[0-9]{20}` at
`SegmentedLog.java:21`, but `segmentName` uses default-locale
`String.format` at line 167. With Java's FORMAT locale set to Arabic, an
independent probe observed the generated name
`٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠.log`; the next `open` rejected it as an invalid segment
name. Thus the reference can reject its own valid output and does not meet the
deterministic 20-digit naming/reopen contract.

Use `Locale.ROOT` (or locale-independent ASCII formatting) and add a locale
regression test.

### P2 — Advertised adversarial coverage exceeds the executable suite

`CANDIDATE/adversarial/README.md:3-11` says the executable inventory includes
truncated length fields, offset/base gaps, and over-leader acknowledgements.
Static inspection of `ReferenceTestMain` found a truncated frame/payload and a
base gap, but no 1-3 byte partial length field, corrupt record-offset gap, or
current-term acknowledgement above the leader. Mandatory corruption branches
for unknown marker/version/flags and inconsistent key metadata are also not
exercised. Neither independent P1 defect is tested.

Add focused deterministic cases for each advertised and mandatory branch, or
qualify the inventory as planned rather than executable. Passing 11 broad
test methods is useful evidence only for their actual assertions.

### P2 — Some sealed expectations are not stated precisely for learners

The reference rejects a record when combined key and value bytes exceed
`maxRecordBytes` (`RecordCodec.java:86-89`), and the sealed suite explicitly
expects that behavior. Learner-facing R1 says only that a value above the
configured limit must be rejected; it never defines whether the key, value,
combined payload, or encoded frame consumes the limit. R7 likewise promises
stable exception categories without mapping invalid inputs and state failures
to categories, although sealed tests assert exact classes.

Publish these behavioral rules in `REQUIREMENTS.md` or an API contract table.
Evaluator checks should not depend on an interpretation unavailable to a
learner or on the sealed implementation's private format choices.

### P2 — Harness timeouts do not enforce the repository's process-group rule

Both Python runners correctly use argv arrays, captured output, and 60-second
timeouts, but `subprocess.run` at `environment/run_public_tests.py:22-29` and
`sealed/run_reference_tests.py:21-28` neither creates nor terminates a process
group. A timeout therefore bounds the direct process but does not guarantee
cleanup of descendants, contrary to the repository instruction that
subprocesses use process groups. Use a process-group-aware wrapper and test its
timeout cleanup deterministically.

## Confirmed strengths

- The starter compiles after a writable build root is supplied, its 1/5 result
  matches the documented progressive TODO state, and milestone numbering plus
  public failure messages give learners a sensible implementation order.
- Requirements, concepts, design prompts, sealed rationale, review exercises,
  and production gaps are clearly separated. The scope avoids claiming a full
  consensus protocol or production broker.
- The submitted public/reference suites reproduced their stated result counts
  with the temp-root workaround, and the layout validator reproduced its
  counts and metadata hashes.
- Metadata is conservative and internally linked. The license boundary marks
  the linked tutorial `NOASSERTION`, says it was not copied, and makes no
  benchmark, fuzz, transfer, security, or production claim.
- Independent tests left `CANDIDATE/` byte-for-byte unchanged according to the
  aggregate hash recorded in `VALIDATION.md`.

## Boundary and label note

The upstream material and actual learner-view construction were unavailable,
so authorship/license lineage and sealed-view exclusion remain limitations,
not validated facts. This REVISE verdict is advisory and does not award
`REVIEWED`; only the orchestrator-controlled acceptance validator may do so.
