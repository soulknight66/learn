# Study Task: A Trustworthy Byte Histogram in C

Estimated effort: 6–10 hours, with 8 hours as the target.

Create all of your work under submission/. Build an executable named build/bytehist.

## Observable contract

Invocation:

~~~text
bytehist
bytehist INPUT
~~~

With no argument, read standard input. With one argument, treat that argument verbatim as the path of a binary input file. There is no option syntax, and a single hyphen has no special meaning.

For successful input, write:

~~~text
total DECIMAL_TOTAL
HH DECIMAL_COUNT
...
~~~

The first line gives the number of bytes read. It is followed by one line for every byte value whose count is nonzero. HH is exactly two uppercase hexadecimal digits. Byte rows are ordered from 00 through FF. Counts use ordinary decimal notation without leading decoration. End every output line with a newline. Successful empty input therefore produces only the total line.

Successful execution writes nothing to standard error and exits with status 0.

If more than one argument is supplied, write exactly the following line to standard error, write nothing to standard output, and exit with status 2:

~~~text
usage: bytehist [INPUT]
~~~

An input, output, or count-range failure must never be reported as success. Exit with status 1 and emit a concise diagnostic beginning with bytehist:. An input failure that occurs before a report is emitted must leave standard output empty.

Treat input as arbitrary bytes, including 00, newline, bytes above 7F, and FF. The total and per-byte counts are unsigned 64-bit quantities. Detect an attempted count overflow instead of silently producing a wrapped result.

## Engineering constraints

- Use C11 and only locally available build and runtime dependencies.
- Keep histogram state and update logic separate from command-line parsing, diagnostics, and process exit behavior.
- Expose the histogram module through a header with a small interface of your own design.
- Process input incrementally; working memory must not grow with input size.
- Account deliberately for short reads, end-of-file, stream errors, output errors, and resource cleanup.
- Compile your own code with at least -std=c11 -Wall -Wextra -Wpedantic -Werror.
- Builds and tests must not access the network or read learner or project data outside the submission workspace. They may use the examiner-provided system toolchain, standard headers and libraries, loader/runtime files, and an isolated temporary directory assigned to the run.
- The clean target may remove only generated products inside the submission.
- Do not include generated binaries or copied solution material in the final submission.

## Required submission

~~~text
submission/
  Makefile
  README.md
  DESIGN.md
  TEST_REPORT.md
  COMPREHENSION_RESPONSES.md
  include/
    bytehist.h
  src/
    bytehist.c
    main.c
  tests/
    ...automated test sources and fixtures...
~~~

The Makefile must provide:

- the default target and make all, producing build/bytehist;
- make test, building as needed and running deterministic automated checks; and
- make clean.

README.md must give exact build, test, and usage commands, plus any known limitation.

DESIGN.md must state:

- the observable and module contracts;
- the invariants connecting the total and the per-byte counts;
- ownership and mutation responsibilities;
- policies for stream failure, output failure, and count overflow; and
- why the chosen module boundary limits coupling.

TEST_REPORT.md must record the compiler and tool environment, the exact commands actually run, their outcomes, and any remaining limitation. Do not invent a run or result. If a diagnostic tool is unavailable, record the attempted command and blocker plainly rather than claiming a pass.

The automated suite must exercise:

- standard input and file input;
- empty, ordinary, and binary data;
- bytes at and above 80 hexadecimal;
- exact output order and formatting;
- too many command-line arguments;
- an unavailable input path; and
- inputs on both sides of more than one processing-chunk boundary.

Expected results must be fixed independently or produced by a test oracle that does not reuse the production histogram implementation.

Copy the question numbers from COMPREHENSION.md into COMPREHENSION_RESPONSES.md and answer them there. Cite relevant files or tests where requested.

## Suggested work sequence

1. Write the contracts, invariants, and failure policies in DESIGN.md.
2. Choose the module interface before implementing the command-line layer.
3. Establish a strict, repeatable build.
4. Implement the smallest program satisfying the contract.
5. Build independent automated checks, including negative cases.
6. Run the checks, record truthful evidence, and complete the comprehension responses.

Stop when the published contract and required artifacts are complete. Record enhancements separately instead of implementing them in this unit.

---

Artifact provenance: course-manager-authored from the supplied CSDIY catalog snapshot at commit adce8e13789dc16aa6d1fbe163e9541736defae4; the task does not reproduce an external assignment.

Validation label: LEARNER_SAFE_TASK_SPECIFICATION_REVIEWED. This label is not evidence that a learner satisfied the task.
