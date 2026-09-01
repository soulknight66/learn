# Independent validation record

Date: 2026-08-31 (America/Chicago)

This is reviewer evidence, not a manifest-label promotion. Candidate-authored scripts were replayed only as corroboration. All candidate commands below ran from `CANDIDATE/`; commands marked “workspace root” ran one directory above it. Functional commands were bounded with `timeout` (10–30 seconds). `CANDIDATE/` was not edited.

## Environment and immutability

Command (workspace root):

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
find CANDIDATE -type l -print | sort
find CANDIDATE -type f | wc -l
du -sk CANDIDATE
```

Observed before checks:

```text
b007464e59a00b94602a56b09724208aeba27b792d1b3dffc24e1e8e1e54a74f  -
(no symlink paths)
55
404 CANDIDATE
```

The aggregate hash was identical after all checks. Files were mode `0444` and directories mode `2555` in this review workspace.

Command:

```sh
command -v ruby
ruby --version
command -v git
command -v rg
command -v jq
command -v timeout
command -v sha256sum
```

Observed:

```text
/usr/bin/ruby
ruby 2.5.9p229 (2021-04-05 revision 67939) [x86_64-linux]
git: unavailable
rg: unavailable
jq: unavailable
/usr/bin/timeout
/usr/bin/sha256sum
```

Ruby is the same version reported by the builder. Only this Ruby version was available, so “2.5 or newer” was not tested as a version matrix. The sandbox also denied writes to `/tmp`; two initial output-capture/heredoc wrappers failed before invoking tests, after which checks were rerun directly from the writable workspace.

## Candidate-authored checks replayed

Command:

```sh
timeout 30s env PEBBLE_LIB=sealed/reference/lib ruby public_tests/test_public.rb
```

Observed exit 0:

```text
............
12 tests, 26 assertions, 0 failures
```

Command:

```sh
timeout 30s ruby -Isealed/reference/lib sealed/reference_tests/test_reference.rb
```

Observed exit 0:

```text
...........................
27 tests, 77 assertions, 0 failures
```

Command:

```sh
timeout 10s ruby sealed/reference/bin/pebble sealed/reference_tests/fixtures/countdown.peb
```

Observed exit 0:

```text
3
2
1
```

Command:

```sh
timeout 30s ruby -Istarter/lib public_tests/test_public.rb
```

Observed exit 1, as intentionally declared:

```text
FFFFFFFFFFFF
12 tests, 6 assertions, 12 failures
```

Eleven failures ended at `Lexer#scan_tokens`; the VM-only case ended at `VM#run`. Both raised the checked-in `NotImplementedError` stubs.

Command:

```sh
timeout 20s ruby sealed/reference_tests/validate_structure.rb
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

This is the builder's checker. It confirms its encoded predicates only; notably, it permits readable material under `sealed/` and does not validate a student-view projection.

## Independent semantic harness

A 138-line reviewer-authored Ruby harness was created outside `CANDIDATE/`, executed, and removed after use. Its SHA-256 was `93d3b800cbb85dab41111bb8217b620b6c54ed25f8f2936c0187d9f50a6ebf2f`. It used direct assertions and did not load the candidate test harness.

Command (workspace root):

```sh
timeout 30s ruby -ICANDIDATE/sealed/reference/lib .review_check.rb
```

Observed exit 1:

```text
PASS lexer token domain, longest match, and source coordinates
PASS lexer rejects invalid alphabet and literal bounds with locations
PASS parser precedence and associativity
PASS parser enforces required blocks, semicolons, and terminal EOF
PASS compiler declaration timing and nearest lexical binding
PASS compiler output is deterministic and structurally resolved
PASS all arithmetic signs, comparisons, equality, and formatting
PASS runtime rejects zero division, wrong types, and overflow
PASS VM rejects malformed bytecode
PASS VM enforces positive step budget
FAIL repeated Lexer#scan_tokens calls still return exactly one EOF: RuntimeError: second result contains 2 EOF tokens
INDEPENDENT_SUMMARY passed=10 failed=1
```

The failing edge is reproducible directly:

```sh
timeout 10s ruby -Isealed/reference/lib -e 'require "pebble"; lexer=Pebble::Lexer.new("print 1;"); first=lexer.scan_tokens; second=lexer.scan_tokens; puts "same_object=#{first.equal?(second)}"; puts "types=#{second.map(&:type).inspect}"; puts "eof_count=#{second.count { |token| token.type == :EOF }}"'
```

Observed exit 0:

```text
same_object=true
types=[:PRINT, :INTEGER, :SEMICOLON, :EOF, :EOF]
eof_count=2
```

## Adversarial and CLI probes

Command:

```sh
timeout 10s ruby -Isealed/reference/lib -e 'require "pebble"; source = "print " + ("!" * 10000) + "true;"; begin; Pebble.compile(source); puts "COMPILED"; rescue Exception => error; puts "OBSERVED_EXCEPTION=#{error.class}"; puts "PEBBLE_ERROR=#{error.is_a?(Pebble::Error)}"; end'
```

Observed exit 0 because the probe caught and reported the exception:

```text
OBSERVED_EXCEPTION=SystemStackError
PEBBLE_ERROR=false
```

Command and observations:

```sh
timeout 10s ruby sealed/reference/bin/pebble
# usage: ruby sealed/reference/bin/pebble FILE
# exit 64

printf 'print 01;\n' | timeout 10s ruby sealed/reference/bin/pebble /dev/stdin
# 1:7: leading zero in integer literal
# exit 1
```

The step-limit, zero-divisor, exact-type, overflow, invalid opcode/arity/constant/local/jump, underflow, and deterministic-compilation cases all passed in the independent harness.

## Syntax, packaging, and dependency inspection

Commands:

```sh
find starter public_tests sealed benchmarks -type f -name '*.rb' -print | sort
# each listed file was passed to ruby -c
ruby -c starter/bin/pebble
ruby -c sealed/reference/bin/pebble
```

Observed: 21 `.rb` files plus two entrypoints, 23 total; zero syntax failures. Both entrypoints printed `Syntax OK`.

Independent targeted scans observed:

```text
symlinks: 0
common private-key/token markers: 0 matches
Ruby/entrypoint files scanned for eval/system/exec/spawn/fork/popen/network primitives: 23
matching files: 0
grep errors: 0
```

All `require` statements resolved to repository-local files or Ruby standard-library `json`, `stringio`, and `find`. Direct environment checks reproduced `LoadError` for both `minitest/autorun` and `test/unit`, matching the builder's explanation.

## Manifest and provenance

Command (workspace root):

```sh
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
```

Observed:

```text
5119170b0732ac97cb5259aea0ae40f919575d015da4e6951149b3eaeda06c68  CANDIDATE/PROVENANCE.json
e5e02d745742e960b72dc1ada9dc54d69bcc021e0b54db6038b1351cf66d496b  CANDIDATE/MANIFEST.yaml
```

Both files parsed as strict JSON, the manifest key set was as submitted, and project/source identifiers agreed. The manifest's named `provenance_sha256` and provenance's `snapshot_sha256` both contain:

```text
e534f25088ceaa9ff361d1831402338ec743bc666427d4b05cb4f56be11ea594
```

That value is not the exported provenance file's SHA-256, and the candidate gives no independent recomputation procedure. The upstream repository, commit, catalog license evidence, and linked article could not be read or fetched in this environment, so copying and external license assertions are inconclusive. Manual inspection found no explicit license grant for the generated material beyond the boundary statement.

## Benchmark-driver smoke check

Command:

```sh
timeout 20s env PEBBLE_LIB=sealed/reference/lib PEBBLE_BENCH_ITERATIONS=1 ruby benchmarks/run.rb
```

Observed exit 0:

```json
{"project_id":"project_0d336967c5b89e5c4851b06a9e793cae","workload":"compile_and_execute_sum_0_to_999","iterations":1,"elapsed_seconds":0.004152054898440838,"validation_label":"UNVALIDATED_MEASUREMENT"}
```

`PEBBLE_BENCH_ITERATIONS=0` was rejected with exit 1. This only checks workload/output gating and driver operation. A single environment-specific timing is not a benchmark and does not support `BENCHMARKED`.

## Limitations

- Candidate-authored tests and prose are corroboration, never authority for validation labels.
- Git, the source snapshot, upstream network access, alternate Rubies, and a license/provenance service were unavailable.
- No student-view projection was supplied, so real sealed-material isolation could not be tested.
- No fuzzing, mutation testing, statistical benchmarking, learner transfer, deployment, or production/security review was performed.
- The manifest was not edited; validator-controlled label promotion remains the orchestrator's responsibility.
