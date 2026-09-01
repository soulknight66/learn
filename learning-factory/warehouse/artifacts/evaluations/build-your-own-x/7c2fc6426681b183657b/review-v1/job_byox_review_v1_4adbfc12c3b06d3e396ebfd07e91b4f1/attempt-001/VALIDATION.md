# Independent validation record

Date: 2026-08-31  
Verdict: `REVISE`

All builds and executable tests ran in `REVIEW_COPY/`, a writable copy of the submitted material.
`CANDIDATE/` was never edited. Its aggregate content digest was identical before and after review:

```text
6705abe0ff6445fce91071033eacd4984b5dd231142f4f934308cf9909234312
```

After evidence capture, the disposable review copy (including binaries and Python caches) was
removed. It is reconstructible from the unchanged candidate.

The digest command was:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

## Environment

Command:

```sh
sh CANDIDATE/environment/check.sh
```

Observed status: 0. Relevant output:

```text
/usr/bin/as
/usr/bin/ld
/usr/bin/make
/usr/bin/python3
GNU assembler version 2.30-123.el8
GNU ld version 2.30-123.el8
Python 3.6.8
```

The command wrapper repeatedly printed numeric-user/group lookup warnings. They were environmental
and did not change command results.

Available inspection tools included `file`, `readelf`, `objdump`, `sha256sum`, and `timeout`.
`strace` was installed but could not use ptrace. `qemu-x86_64`, `valgrind`, `git`, and `rg` were
unavailable.

## Submitted build and test commands

| Command (from `REVIEW_COPY/`) | Status | Observed result |
| --- | ---: | --- |
| `python3 -m unittest discover -s public_tests -v` | 1 | 10 tests; 8 failures and 2 passes, matching the documented incomplete starter baseline |
| `STACKVM_TARGET="$PWD/sealed/reference" python3 -m unittest discover -s public_tests -v` | 0 | 10 tests; `OK` |
| `python3 -m unittest discover -s sealed/reference_tests -v` | 0 | 11 tests; `OK` |

Passing builder-supplied suites was treated as corroboration only, not as proof of any validation
label.

## Independent behavioral check

A reviewer-authored inline Python harness implemented tokenization, signed-literal validation, the
ten stack words, checked signed arithmetic, compile-before-execute behavior, stack capacity, exact
diagnostics, and the 4,095/4,096-byte boundary directly from R3-R10. It ran each case through the
reference with an argv array, captured streams, and a two-second timeout. The case set comprised 27
explicit boundary/adversarial inputs plus 600 deterministic generated token streams using
`random.Random(20260831)`. Generation included signed extrema, malformed values, all words,
non-ASCII tokens, and separator bytes `0x00`, `0x09`, `0x0a`, `0x1f`, and `0x20`.

Invocation shape:

```sh
cd REVIEW_COPY
python3 - <<'PY'
# Inline independent R3-R10 oracle and deterministic case generator.
# Each subprocess used [sealed/reference/stackvm], captured stdout/stderr,
# timeout=2, and compared (returncode, stdout, stderr) exactly.
PY
```

Observed status: 0.

```text
seed=20260831
reviewer_authored_cases=627
mismatches=0
expected_status_counts={0: 43, 2: 547, 3: 29, 4: 3, 6: 2, 7: 3}
```

This was bounded deterministic sampling, not a fuzz campaign and not `FUZZED` evidence. The
generated set happened not to produce an oracle status-5 case, so a separate reviewer-authored
direct invocation covered it:

```text
division_zero_returncode=5
division_zero_stdout=b''
division_zero_stderr=b'division by zero\n'
```

A separate delayed feed wrote `12 3 + .` one byte at a time with 30 ms between writes:

```text
delayed_byte_writes_returncode=0
delayed_byte_writes_stdout=b'15\n'
delayed_byte_writes_stderr=b''
```

This supports accumulation behavior but does not prove individual kernel read boundaries. The
attempted trace:

```sh
printf '2 3 + .\n' | strace -qq -e trace=read,write,exit,exit_group,open,openat,socket,connect \
  ./sealed/reference/stackvm
```

failed with status 1 and `PTRACE_TRACEME: Operation not permitted`.

## Rebuild and binary inspection

Commands:

```sh
make -C sealed/reference clean all
sha256sum sealed/reference/stackvm
make -C sealed/reference clean all
sha256sum sealed/reference/stackvm
file sealed/reference/stackvm
readelf -h sealed/reference/stackvm
readelf -W -l sealed/reference/stackvm
readelf -W -S sealed/reference/stackvm
readelf -d sealed/reference/stackvm
nm -u sealed/reference/stackvm
```

Both clean builds succeeded and produced the same digest:

```text
d5832caaf9b900cc6ff78f6f0c53e4c31018fe6c6095a12be10475b547b99baf
```

Observed binary facts:

- ELF64, little-endian, `EXEC`, AMD x86-64, entry point `0x4000e8`.
- Statically linked; no dynamic section and no undefined symbols.
- One `R E` load segment for `.text/.rodata`, one `RW` segment for `.bss`, and no RWX segment.
- `GNU_STACK` is `RW`, not executable.
- Static disassembly contained five `syscall` instruction sites. Source inspection associated them
  only with read, write, and exit paths; ptrace-based runtime confirmation was unavailable.

A closed stdout was also tested. The program returned 9 and wrote
`internal bytecode error\n` to stderr, confirming the behavior disclosed in the sealed self-review
and the status-9 contract ambiguity described in `REVIEW.md`.

## Benchmark harness

Command:

```sh
cd REVIEW_COPY
python3 sealed/benchmarks/benchmark.py sealed/reference/stackvm
```

Observed status: 1 before the target ran:

```text
AttributeError: module 'time' has no attribute 'perf_counter_ns'
```

The declared Python is 3.6.8. Independently calculating the default generated source length gave:

```text
benchmark_default_input_bytes=40003
contract_max_accepted_bytes=4095
```

Thus no benchmark measurement was obtained and no `BENCHMARKED` conclusion is supported.

## Metadata, provenance, hygiene, and disclosure

Strict `json.load` hooks rejecting duplicate keys and non-JSON constants parsed both
`MANIFEST.yaml` and `PROVENANCE.json`. The following internal checks were true:

```text
project_id_match=true
source_id_match=true
source_commit_match=true
snapshot_binding_match=true
linked_license_noassertion=true
linked_copy_claim_false=true
manifest_partial_only=true
productionized_false=true
```

`find` found no symlink or special file, and a recursive scan found no AWS access-key shape,
private-key header, bearer credential, or quoted password/key/secret assignment. These pattern
checks do not prove absence of every possible secret.

The linked source and catalog snapshot were outside the readable workspace and network access was
restricted, so the recorded commit, catalog license evidence, and no-copy assertion could not be
compared with the originals. Internal provenance consistency passed; external provenance remains
inconclusive.

Commands:

```sh
test -r CANDIDATE/sealed/reference/stackvm.S
test -r CANDIDATE/sealed/reference_tests/test_reference.py
```

Both returned 0. The candidate contains a prose learner allowlist but no supplied exporter, ACL, or
transfer record proving those readable sealed paths are excluded from an actual student view.
Consequently progressive disclosure and transfer verification remain inconclusive, and serving the
submitted tree directly would disclose the solution and evaluator cases.

## Claim boundaries

This review does not award or imply `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED`. It records bounded observations from one native x86-64
host. No sanitizer, profiler, emulator, portability matrix, benchmark measurement, upstream
comparison, production hardening, or transfer validation was completed.
