# Revision Debugging Log

This is a reproducible record of hypotheses, commands, observations, and changes. It omits private
deliberation and does not turn static inspection into runtime evidence.

## 1. Failure classification and workspace inventory

**Hypothesis:** The examiner failure was caused by an absent deliverable tree, not by a reported
operator assertion.

**Experiment:** Read the supplied learner brief, study task, comprehension prompt, prior three records,
and examiner feedback. Listed files only inside this attempt workspace.

**Observation:** The initial workspace contained the read-only learner material, prior records,
feedback/job metadata, and no current `src/`, design, run, manifest, comprehension, or test-output
artifact. The feedback explicitly scored every executable area zero because those files were absent.

**Action:** Left all supplied directories unchanged and built a fresh current submission tree. I did
not inspect a rubric, reference answer, hidden check, sealed source, another learner's work, or factory
state.

## 2. Toolchain discovery

**Hypothesis:** This revision workspace might have a compiler even though the prior workspace did not.

**Experiment:** Used shell command lookup for `javac`, `java`, `jshell`, `ecj`, `gcj`, `ant`, `mvn`,
and `gradle`; also attempted `java -version` and `javac -version`.

**Observation:** Every Java/compiler/build command was unavailable. The version commands returned
`command not found`. No network or installation attempt was made.

**Action:** Kept the implementation dependency-free and made JDK 8+ an explicit `RUN.md` prerequisite.

## 3. Executable package reconstruction

**Hypothesis:** A narrow shared lifecycle plus immutable data objects can express all required behavior
without coupling the four operators to concrete children.

**Experiment:** Implemented 21 production files and one separate test file. Traced the composed sample
by hand through two filters, projection, and limit. Modeled normal exhaustion, early root close,
zero-limit behavior, repeated EOS, and failed child open against the shared state transitions.

**Observations:** The sample's second output is available after source row four, so a correctly bounded
limit need not pull row five. Setting `CLOSED` before invoking cleanup makes repeated close idempotent
even if cleanup throws. Marking a unary child open attempt before calling it lets parent rollback cover
a custom child that fails during acquisition.

**Action:** Centralized transitions in `AbstractOperator`, child propagation in
`AbstractUnaryOperator`, eager predicate/project validation in constructors, and child-pull/close
counters in the tests.

## 4. Deterministic static checks

**Hypothesis:** File identity and coarse Java structure can be checked without pretending to compile.

**Experiments:** Parsed the manifest with `python3 -m json.tool`. Ran a comment/string-aware lexical
stack over every Java source, checked each public top-level type against its filename, checked imports,
and compared manifest paths with inventory lines. Emulated the specified `java.util.Random` sequence
independently for seed `0x5EEDC0DE`.

**Observations:** There are 22 Java files; the lexical/import checker reported zero errors. The manifest
and inventory each contain the same 32 paths. The emulated data has 102 records satisfying
`score > 15 && score < 70`, so limit 37 is non-vacuous. `javalang` and tree-sitter Java parsers were not
installed, so these checks do not establish grammar or type correctness.

**Action:** Preserved these results as static evidence only. I did not label any test passed.

## 5. Safe clean-build command correction

**Hypothesis:** A conventional command that recursively removes only `build/` would be accepted as a
clean build step.

**Experiment:** Tried the first documented block containing `rm -rf -- build`.

**Observation:** The workspace safety layer rejected the entire command before it ran because recursive
deletion is disallowed. It produced no compiler result or capture.

**Action:** Replaced deletion with `mktemp -d ./build-attempt.XXXXXX`. Each run now receives a new empty
class directory and retains its scratch evidence. Updated `RUN.md`, the manifest commands, and their
checksums before attempting compilation.

## 6. Content identity

**Hypothesis:** The stable implementation and contract files match their recorded digests.

**Experiment:** Ran `sha256sum -c SUBMISSION_SHA256SUMS.txt` after the command correction.

**Observation:** All 27 entries reported `OK`. The checksum file itself hashed to
`38732dfea0a0625bea7298b3d5e903c7c1e8da0b51cb1f38f5caf3335855ee79` during the clean attempt.

**Scope:** The digest set contains all 22 Java files plus `DESIGN.md`, `RUN.md`,
`COMPREHENSION_RESPONSE.md`, `SUBMISSION_MANIFEST.json`, and `artifact-inventory.txt`. It excludes
itself, the mutable test capture, and the three revision narratives. Those paths remain in the complete
inventory.

## 7. Fresh documented build/test attempt

**Hypothesis:** The revised `RUN.md` block would create a clean scratch tree, identify the source, and
stop visibly at the unavailable compiler without claiming test execution.

**Experiment:** Ran the Bash block exactly as documented.

**Observation:** It created `./build-attempt.3s6iwz`, wrote a 22-line sorted `sources.list`, printed the
checksum-file identity, and attempted:

```text
javac -encoding UTF-8 -source 8 -target 8 -Xlint:all \
  -d ./build-attempt.3s6iwz/classes @./build-attempt.3s6iwz/sources.list
```

The shell reported `javac: command not found`; `test-output.txt` ends with
`COMMAND_EXIT_STATUS=127`. The `java` argv was intentionally never reached. The class directory is
empty, and the output has no `PASS` or `SUMMARY` line.

**Conclusion:** The feedback's missing-artifact problem is addressed in the current workspace, but
compilation, learner test success, evaluator validation, and artifact transfer are all unverified. The
next evidence-producing action is the unchanged documented run in a harness that supplies JDK 8+.
