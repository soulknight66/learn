# Local validation record

Status remains **GENERATED + PARTIAL**. These are worker-local observations,
not independent evidence and not authorization for `BUILDS`, `TESTED`,
`FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
`PRODUCTIONIZED` labels.

Validation was performed in the allocated workspace on 2026-08-31. The linked
upstream tutorial was not fetched or inspected; it is provenance only. No
network dependency was needed.

## Host tools observed

```text
$ cc --version
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)

$ make --version
GNU Make 4.2.1

$ python3 --version
Python 3.6.8
```

The sandbox command wrapper also printed `id` warnings because numeric user and
group names are absent in its minimal account database. Those launcher warnings
did not alter any command exit status below.

## Starter and public checks

Exact command:

```sh
make -C starter clean all && \
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s public_tests -v
```

Observed: exit 0. GCC compiled five C sources with C11,
`-Wall -Wextra -Wpedantic -Werror`, and dependency generation; the archive and
`starter/minish` linked successfully. Unittest reported:

```text
Ran 9 tests in 0.529s

OK
```

The nine checks covered the documented files/API link, CLI help, missing and
unknown option errors, physical-line splitting of an embedded-newline `-c`
operand, empty commands, quiet batch EOF, and rejection of an embedded NUL
before the incomplete language stages. The starter deliberately returns a TODO
error for nonempty shell language; this passing baseline is not a completed
learner solution.

## Sealed reference checks

Exact command:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 sealed/reference_tests/test_reference.py -v
```

Observed: exit 0. The suite first performed a clean strict reference build, then
reported:

```text
Ran 51 tests in 2.473s

OK
```

The black-box cases exercised CLI forms, physical-line behavior, NUL rejection,
quotes/escapes/empty arguments, operator precedence, whole-line syntax
validation, concurrent large pipelines, final-stage statuses, `ENOENT` and
`ENOTDIR`, semantic 126/127 handling including a missing shebang interpreter,
`execvp` text-file fallback, all three redirections, parent redirection rollback,
builtin context, arbitrary-length exit status, distinct current/foreground
status memory, process groups, strict job-ID syntax, stable job text,
running/stopped/completed jobs, `fg`/`bg`, rightmost-stopped-member status,
background `/dev/null`, and bounded shutdown. Four real pseudo-terminal cases
verified Ctrl-C and prompt recovery, controlling-terminal handoff with stdout
redirected, immediate-reader launch ordering, and suppression of prompt-only
notices for terminal-attached `-c` mode.

## Adversarial corpus

Exact command:

```sh
python3 adversarial/run.py --timeout 5 sealed/reference/minish
```

Observed: exit 0; all 10 cases were labelled `completed(status=0)`, with no
timeout or signal termination. Notable observed values were 1,048,576 bytes
through the bulk pipeline, three lines before early-consumer exit, and seven
bytes through the 16-stage pipeline. Case 08 intentionally emitted one syntax
diagnostic and then ran its next valid physical line. The runner is not an
oracle, so completion does not convert these observations into a validation
label.

The session-wide timeout cleanup path was forced with:

```sh
python3 adversarial/run.py --case 04-large-pipeline.minish \
  --timeout 0.0001 sealed/reference/minish
```

Observed: the runner intentionally returned 1 and labelled the case `TIMEOUT`.
A subsequent `ps` scan found no `minish`, `head`, or `wc` survivor. This checks
the harness cleanup path; it is not a failed reference behavior at the normal
deadline.

## Exercise-source compilation

Exact compiler form, run for all eight exercise sources:

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -Werror -fsyntax-only PATH
```

Observed: exit 0 for the buggy and fixed sources in `debugging/eof_hang`,
`debugging/token_vector`, and `debugging/wait_race`, plus the buggy sources in
`review_exercises/job_table` and `review_exercises/pipeline_launcher`. The bugs
are behavioral/ownership exercises rather than compiler-warning exercises.

## Benchmark-harness smoke only

Exact command:

```sh
python3 benchmarks/run.py --iterations 1 --warmup 0 sealed/reference/minish
```

Observed: exit 0, with these single-sample wall-clock values:

```text
workload                 median ms     p95 ms     min ms     max ms
builtin_pwd                   2.992      2.992      2.992      2.992
builtin_list_20               3.043      3.043      3.043      3.043
external_true                 3.789      3.789      3.789      3.789
pipeline_128k                 5.291      5.291      5.291      5.291
pipeline_8                    6.930      6.930      6.930      6.930
background_burst              4.063      4.063      4.063      4.063
```

One sample is only a harness smoke test. These values are not a stable baseline
and do not support a `BENCHMARKED` claim.

## Informative failed attempts and unavailable evidence

The documented AddressSanitizer build was attempted exactly as follows:

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -O0 -g \
  -fsanitize=address -fno-omit-frame-pointer \
  debugging/token_vector/sealed/fixed.c \
  -o debugging/token_vector/asan-fixed
```

Observed: exit 1; the linker reported:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
collect2: error: ld returned 1 exit status
```

No sanitizer binary was produced. The host therefore cannot supply sanitizer
evidence for this artifact without installing the matching runtime.

An early version of the Ctrl-C PTY test timed out while waiting for a recovered
prompt. Investigation showed the harness had matched `READY` inside the
terminal's echoed command text and sent Ctrl-C before the child was launched.
The test now disables terminal echo before sending the command and waits for a
marker written by a foreground process that first confirms its terminal PGID.
The corrected case passes in the 51-test run above. A separate immediate-reader
case queues a command and its payload together and confirms that the new launch
barrier transfers terminal ownership before the child can read.

No fuzzer, leak checker, syscall fault injector, profiler, cross-platform CI, or
external validator was available or run. The manifest therefore intentionally
remains `GENERATED` and `PARTIAL`, with `productionized: false` and independent
validation required.

## Packaging checks

The final pass parsed both JSON-bearing metadata files with duplicate-key
rejection and compared them as objects to the authoritative inert blocks in the
allocated job description. Observed:

```text
strict-json-ok MANIFEST.yaml
strict-json-ok PROVENANCE.json
authoritative-object-equality-ok manifest provenance
cross-identity-ok project provenance source
```

An explicit path-array check then observed all 23 required paths as regular
files and all 21 forbidden paths absent. A generated-material scan using common
AWS, GitHub, Slack, private-key, password/key/token assignment, and credentialed
URL patterns reported no match. Final filesystem checks reported:

```text
special-files-ok 0
symlinks-ok 0
scratch-files-ok 0
scratch-directories-ok 0
```

The scratch check covered objects, archives, bytecode, built `minish` binaries,
the failed sanitizer output name, `build/`, and `__pycache__/`. The validated
binaries were removed with their documented clean targets after testing. A
successful Codex exit is not treated as additional evidence.
