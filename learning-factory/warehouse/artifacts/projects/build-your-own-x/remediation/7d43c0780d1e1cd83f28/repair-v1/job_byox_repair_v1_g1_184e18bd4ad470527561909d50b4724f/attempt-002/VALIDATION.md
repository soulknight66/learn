# Repair validation record

## Outcome and evidence boundary

This repair remains **GENERATED + PARTIAL** and requires fresh independent
validation. The route-dispatch implementation and sealed regression source were
repaired, but no Node.js-compatible runtime or container runner exists on this
host. Therefore no JavaScript build, test, adversarial, or benchmark success is
claimed. The pack has not earned `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

All commands in this record were run afresh from the repaired pack root on
2026-08-31. Results copied from `PRIOR_BUILD/` or `PRIOR_REVIEW/` were not used
as validation evidence. Login-shell startup printed unrelated UID/GID
name-lookup warnings before commands; those warnings do not originate in the
pack and are omitted from the output excerpts below.

## Repair-specific source and harness checks

The reference dispatcher now caches a fresh empty params object when capture
materialization throws. This lets a later error handler in the same route
registration run without invoking the failing decoder again. The new sealed
test exercises both that route-local path and a separate later global error
handler. These are source observations only because the Node test run was
unavailable.

Test declarations were counted without treating them as results:

```bash
awk '/^[[:space:]]*test\(/ {count += 1} END {print count + 0}' public_tests/*.test.js
awk '/^[[:space:]]*test\(/ {count += 1} END {print count + 0}' sealed/reference_tests/*.test.js
```

Observed output was `21` and `34`, respectively. The sealed count increased by
one regression; neither number is a pass count.

## Learner-view isolation

`environment/learner-view-policy.json` is an exact allowlist. Its verifier reads
only those source files, rejects unsafe or solution-bearing path components,
and computes a deterministic prospective-view digest without creating a
workspace:

```text
$ python3 environment/export-learner-view.py verify
{"digest_algorithm": "learner-view-sha256-v1", "file_count": 23, "sha256": "d1fb33d5b341307feb163c8cdab32aeea7c7725de2269ddd2887b1ead964822d"}
exit 0
```

The production pack intentionally contains evaluator material, but none of its
paths is reachable from the allowlist. The exporter also guards the production
workspace itself:

```text
$ python3 environment/export-learner-view.py export ./learner-view-must-not-exist
FAIL learner view: destination must be outside the production pack
exit 1

$ test ! -e learner-view-must-not-exist
exit 0
```

No learner workspace was created in this production-builder allocation. The
digest above is builder-controlled prospective evidence, not an independently
checked transfer artifact. An authorized delivery controller must export to a
separate allocated destination, recompute the digest, and independently verify
the resulting inventory before any `TRANSFER_VERIFIED` claim.

The isolation change has deterministic sealed `unittest` coverage. Bytecode
writing was disabled so the check left no cache artifacts:

```text
$ python3 -B -m unittest sealed/learner_view_tests.py -v
test_allowlist_cannot_reach_denied_prefixes (sealed.learner_view_tests.LearnerViewPolicyTests) ... ok
test_export_refuses_the_production_root_without_writing (sealed.learner_view_tests.LearnerViewPolicyTests) ... ok
test_receipt_is_exact_and_repeatable (sealed.learner_view_tests.LearnerViewPolicyTests) ... ok
test_solution_bearing_components_are_rejected (sealed.learner_view_tests.LearnerViewPolicyTests) ... ok
Ran 4 tests in 0.022s
OK
exit 0
```

## Process-level boundedness

The JavaScript helpers retain in-process request timers and byte ceilings, and
their documentation now states that those timers require the event loop to
yield. `environment/run-bounded.py` supplies a separate process-group
wall-clock boundary, uses an argv array without a shell, merges and captures at
most 2 MiB of output, and sends TERM then KILL when necessary.

A normally exiting command was observed:

```text
$ python3 environment/run-bounded.py 5 -- python3 -c "print('runner-ok')"
runner-ok
exit 0
```

A synchronous non-yielding command was stopped by the outer boundary:

```text
$ python3 environment/run-bounded.py 1 -- python3 -c "while True: pass"
[runner] wall-clock deadline exceeded: 1.0 seconds
exit 124
```

Both commands use Python's argv interface; the quoted `-c` argument is not a
shell command string.

## Runtime discovery and JavaScript attempts

```bash
for tool in node npm nodejs bun deno qjs js docker podman apptainer singularity; do
  command -v "$tool" || true
done
```

Observed: no command printed a path. The loop exited 0 because missing tools are
explicitly tolerated for discovery.

```text
$ python3 --version
Python 3.6.8
exit 0
```

The intended JavaScript checks were still attempted after the repair:

```text
$ node --test public_tests/*.test.js
/bin/bash: node: command not found
exit 127

$ node --test sealed/reference_tests/*.test.js
/bin/bash: node: command not found
exit 127

$ node adversarial/run.js
/bin/bash: node: command not found
exit 127

$ node benchmarks/router-benchmark.js
/bin/bash: node: command not found
exit 127
```

The benchmark produced no measurement. No dependency was downloaded and no
network or upstream checkout was accessed.

## Metadata and structure

The following strict-JSON parses exited 0 with no output:

```bash
python3 -m json.tool MANIFEST.yaml >/dev/null
python3 -m json.tool PROVENANCE.json >/dev/null
python3 -m json.tool environment/learner-view-policy.json >/dev/null
python3 -m json.tool starter/package.json >/dev/null
python3 -m json.tool sealed/reference/package.json >/dev/null
```

Immutable and package hashes were observed as:

```text
$ sha256sum MANIFEST.yaml PROVENANCE.json starter/package.json sealed/reference/package.json
a4529eb3613733b2930841b447d4495d38f6945c54363fb61cee0132207c8dbd  MANIFEST.yaml
dc328469b4988520ffa7a9d9f58e207914721720b1a6d93bac854dcad0796f05  PROVENANCE.json
7c9146726d251329f5828e93d4ba00dfb438c626f042edaf3441eecc9dd98650  starter/package.json
d72d3b5a395ae904abe5992346651a93e1b1b99289ddcc1ecf85a85c5aebd6a3  sealed/reference/package.json
exit 0
```

The full-pack structural verifier checks the authoritative required and
forbidden path lists with `lstat`, rejects symlinks and special files within
artifact roots, and checks the immutable metadata hashes:

```text
$ python3 environment/verify-structure.py
PASS required paths: 23 regular files
PASS forbidden paths: 21 absent
PASS artifact node types: 67 files, 25 directories
PASS immutable metadata: strict JSON and expected SHA-256
exit 0
```

This verifier and the learner-view verifier are builder-controlled checks, not
independent validation.

## Credential-oriented scans

The following targeted scan asks only for filenames containing a high-confidence
private-key or provider-token signature:

```bash
grep -RIlE -- '-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-(proj-)?[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}' README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks
```

Observed output was empty and grep exited 1 (no match). A credential-assignment
scan also produced no filenames and exited 1:

```bash
grep -RIlE -- '(password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret)[[:space:]]*[:=][[:space:]]*[^[:space:]]{8,}' README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks
```

Finally:

```bash
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks -type f \( -iname '*.pem' -o -iname '*.key' -o -iname '*credential*' -o -iname '*secret*' \) -print
```

Observed output was empty and `find` exited 0. These narrow scans reduce risk but
are not a general secret detector.

## Remaining limitations

- JavaScript syntax and behavior, including the repaired dispatch regression,
  remain unexecuted on this host.
- The allowlisted learner view was verified virtually but was not materialized
  or transferred; transfer isolation still requires independent evidence.
- Benchmarking, fuzzing, supported-version coverage, and production evaluation
  were not performed.
- `LICENSE_BOUNDARY.md` now explicitly provides no reuse or redistribution
  grant for generated material; this is a boundary statement, not legal review.

The manifest therefore remains exactly `GENERATED` + `PARTIAL`, with
independent validation required.
