# Debugging Log

This log records reproducible hypotheses, commands, observations, changes, and lessons. It is not a
private reasoning transcript.

## 1. Learner-safe input discovery

**Hypothesis:** The workspace exposes three clearly named learner course files, and no repository-wide
inspection is needed.

**Experiment:** Tried `rg --files` for filename discovery. The command failed because `rg` is not
installed. Used a shallow `find . -maxdepth 2 -type f -print` fallback, then opened only
`COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`.

**Observation:** The shallow listing also named `.factory-workspace` and `JOB.md`; neither was opened.

**Lesson/action:** Tool failure should narrow the fallback, not broaden the search. No rubric, sealed
reference, factory state, other learner work, or repository metadata was consulted.

## 2. Java toolchain availability

**Hypothesis:** A Java course workspace would have `java` and `javac` available on `PATH`.

**Experiments:** Ran `java -version`, `javac -version`, and then checked `module`, `java`, `javac`, and
`jshell` through the shell's command lookup.

**Observation:** `java`, `javac`, and `jshell` were absent; the `module` command was also unavailable.
The effective `PATH` contained standard system directories but no JDK command.

**Action:** Kept the implementation dependency-free, did not use the network or install unrecorded
software, and planned an honest nonzero captured build attempt.

**Lesson:** Environment assumptions belong in `RUN.md`, and an authored test suite is not an executed
test suite.

## 3. Production/test API integration review

**Hypothesis:** Independently drafted production and tests would agree on lifecycle and lookup behavior.

**Experiment:** Compared the learner-generated public methods with every test call before attempting a
build.

**Failures found:**

- `Schema.indexOf` documents and implements `-1` for a missing name, but one test expected
  `SchemaException`.
- The contract requires close-before-open to fail, but one test called it as though it transitioned to
  closed.

**Action:** Changed the lookup test to assert `-1`. Changed close-before-open to expect
`LifecycleException`, then verified that the still-`NEW` object can open and close normally.

**Lesson:** Exception taxonomy is only useful when tests assert the public boundary instead of an
internal helper convention.

## 4. Observability gaps in boundary tests

**Hypothesis:** Checking that limit zero returns an empty result is sufficient.

**Experiment:** Considered an incorrect implementation that pulls and discards one child row before
returning EOS. It would still satisfy the original output-only assertion.

**Action:** Added a counting child and asserted zero pulls plus one propagated close. Added related
checks for no over-pull after limit one, text equality, projected column types, immutable projection
metadata, and repeated composed EOS without another source pull.

**Lesson:** Side-effect and ownership contracts need spies or counters; output equality cannot observe
hidden upstream work.

## 5. Failed-open cleanup

**Hypothesis:** Handling normal and early close paths covers lifecycle resource safety.

**Experiment:** Static review modeled a future operator whose open hook acquires something and then
throws.

**Failure found:** The original shared lifecycle left the object `NEW` and supplied no deterministic
rollback path.

**Action:** A failed open now makes the operator terminal, invokes its close hook once, rethrows the
original failure, and attaches a distinct cleanup failure as suppressed. Unary operators mark the
child open attempt before calling it so a throwing custom child receives one cleanup attempt. Tests
exercise a failing subclass hook, a failing custom child, and simultaneous open/rollback failures to
verify that the cleanup error is suppressed exactly once.

**Lesson:** Production lifecycle design must include partial initialization, not just steady-state
iteration.

## 6. Documentation and provenance consistency

**Hypothesis:** Draft documentation matched the final test implementation and manifest requirements.

**Experiment:** Compared the generated-test description, runtime/build fields, complexity table, and
capture command with the current learner-generated sources.

**Failures found:** The first comprehension draft described a different randomized predicate; the
manifest omitted an explicit runtime and commands; the original capture redirected only test output,
so a compiler failure would leave an empty file; scan construction understated worst-case schema-check
cost.

**Action:** Documented the actual seed and predicates, added JDK/runtime and command fields, captured
the whole build/test attempt plus status, and corrected scan construction to `O(nw)` worst case.
`python3 -m json.tool SUBMISSION_MANIFEST.json` succeeded. A simple per-file brace-count check reported
all Java braces balanced.

A later attempt to generalize that shell delimiter check packed all delimiter pairs into one loop
token and printed a false mismatch. I discarded that result rather than treating a checker bug as a
source bug, then replaced it with a comment/string-aware lexical stack scan. The corrected scan found
balanced nested delimiters in all 19 Java files.

I also independently emulated `java.util.Random` for seed `0x5EEDC0DE`; 103 of 240 generated scores
meet `score > 15 && score < 70`, confirming that the oracle reaches limit 37. This checks the test-data
assumption only; it does not execute Java production code.

**Lesson:** Provenance files must describe the command that actually ran and must remain useful on a
failure path.

## 7. Final clean build/test attempt

**Hypothesis:** The documented command would fail at the already observed missing compiler and record
that failure without implying test execution.

**Experiment:** Ran the exact block from `RUN.md` after final source integration.

**Observation:** `test-output.txt` contains:

```text
PROVENANCE=RUN.md clean build/test command
VALIDATION_LABEL=LEARNER_GENERATED_UNVALIDATED
sh: line 22: javac: command not found
COMMAND_EXIT_STATUS=127
```

No class files were compiled, the Java test main did not run, and no test `SUMMARY` was produced.

**Conclusion:** The bounded kickoff is an uncompiled, unvalidated learner attempt. The next experiment
is the same command on a JDK 8+ environment, followed by fixes driven by compiler/test evidence.
