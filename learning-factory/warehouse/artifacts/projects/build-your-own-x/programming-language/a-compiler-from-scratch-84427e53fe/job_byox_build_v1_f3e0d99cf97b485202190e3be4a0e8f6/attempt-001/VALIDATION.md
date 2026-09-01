# Generation-time validation record

Status remains **GENERATED + PARTIAL**. These are worker-local observations, not independent validation labels. The starter is intentionally incomplete; only the sealed reference is expected to pass.

## Environment

Command:

```sh
ruby --version
```

Observed exit 0:

```text
ruby 2.5.9p229 (2021-04-05 revision 67939) [x86_64-linux]
```

No network access or upstream-content fetch was attempted. No gems were installed.

## Final functional checks

Command:

```sh
PEBBLE_LIB=sealed/reference/lib ruby public_tests/test_public.rb
```

Observed exit 0:

```text
............
12 tests, 26 assertions, 0 failures
```

Command:

```sh
ruby -Isealed/reference/lib sealed/reference_tests/test_reference.rb
```

Observed exit 0:

```text
...........................
27 tests, 77 assertions, 0 failures
```

Command:

```sh
ruby sealed/reference/bin/pebble sealed/reference_tests/fixtures/countdown.peb
```

Observed exit 0:

```text
3
2
1
```

Command (expected incomplete learner state):

```sh
ruby -Istarter/lib public_tests/test_public.rb
```

Observed exit 1. Each case stopped at an intentional stage stub (`Lexer#scan_tokens` or `VM#run`):

```text
FFFFFFFFFFFF
12 tests, 6 assertions, 12 failures
```

## Informative failed attempts

The first reference/public run used `require "minitest/autorun"`:

```sh
PEBBLE_LIB=sealed/reference/lib ruby public_tests/test_public.rb
```

Observed exit 1 with `LoadError: cannot load such file -- minitest/autorun`. A direct `require "test/unit"` check produced the same kind of `LoadError`. The suite was therefore converted to the checked-in dependency-free harness; `require "json"` was observed available.

An early sealed-suite run observed:

```text
27 tests, 76 assertions, 1 failures
expected [3, 19], got [3, 18]
```

Manual column counting showed that EOF after `// tail` is at column 18; the test expectation was corrected. No implementation behavior was weakened to make the test pass.

## Static and packaging checks

Command:

```sh
ruby sealed/reference_tests/validate_structure.rb
```

Observed exit 0:

```text
required files: 23/23
forbidden paths present: 0
non-regular generated entries: 0
credential-pattern matches: 0
solution-bearing filenames outside sealed: 0
manifest strict object: OK
provenance strict JSON and identifiers: OK
generated regular files scanned: 55
```

Commands:

```sh
ruby -c starter/bin/pebble
ruby -c sealed/reference/bin/pebble
find starter public_tests sealed benchmarks -type f -name '*.rb' -print0 | sort -z | xargs -0 -n 1 ruby -c
```

Observed exit 0 with 23 `Syntax OK` lines. Tool-launched commands also printed three `/usr/bin/id` name-resolution warnings for the sandbox's numeric user/group IDs; these were environment noise and did not change command exit status or program output.

## Claims deliberately not made

The benchmark driver was not executed, no fuzzer was run, no external review occurred, and no transfer or production deployment was attempted. Accordingly this record does not claim `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`; those labels require the orchestrator's independent validators.
