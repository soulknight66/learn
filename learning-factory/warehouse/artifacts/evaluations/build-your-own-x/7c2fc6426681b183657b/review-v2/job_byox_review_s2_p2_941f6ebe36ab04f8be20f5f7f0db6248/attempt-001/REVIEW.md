# Independent review

## Verdict: REVISE

The educational content and reference implementation are strong enough to retain: native and
QEMU smoke builds worked, the 10 public and 13 sealed reference tests passed, and an independent
46-process assertion harness found no language-behavior failure. The revision is required because
the deterministic build and audit claims are materially stronger than the tooling actually
enforces. This verdict does not award or publish a `REVIEWED` label.

## Prioritized findings

### P1 — Identical builds are not byte-reproducible

`environment/build.py:66-70` gives the linker an object filename inside a randomly named
`TemporaryDirectory`. GNU ld retains that argument in the unstripped symbol string table. Two
same-source, same-tool, same-command builds therefore differed:

```text
168135573ab6c105edea98a0c8c2c0ef3ed1044baf944079634b56129c811896  repro-a
3b212d83269df78e2b9bc0e7fd693f1600f41dd4a5ac37c8c390386347906b1f  repro-b
```

The only observed cause was the embedded `cinder-build-*/cinder.o` path. This also leaks the
workspace path into an output described as reproducible. Link using a stable object argument (for
example, a fixed basename with a controlled working directory) or deliberately strip the
non-runtime symbol data, then add a unittest that builds twice and compares bytes.

### P1 — The structure audit does not require the functional artifact

The `REQUIRED` tuple at `environment/audit.py:16-40` requires documentation but omits the core
starter, public test, build, audit, and benchmark files. In particular, the audit can report
`required_regular: 23` even if these are absent:

```text
starter/forth.S
starter/Makefile
public_tests/test_cinder.py
environment/build.py
environment/audit.py
benchmarks/run.py
```

The current submission does contain all six, so this is an evidence defect rather than a missing
artifact today. Make the inventory complete (including evaluator executables where applicable), or
validate a checked-in deterministic file manifest. Add negative unittests that remove each
required functional file from a fixture and require audit failure.

### P2 — The documented non-symlink tool policy is not enforced

At `environment/build.py:56-63`, all three inputs are resolved before `is_symlink()` is evaluated.
Resolution removes the evidence that the supplied path was a symlink. A review invocation using
symlinks for the source, assembler, and linker returned 0 and produced an ELF, contrary to both the
parser error text and `environment/README.md:5-6`.

Check the supplied paths with `lstat`/`is_symlink()` before resolution, then validate the resolved
targets. Cover source, assembler, and linker separately with deterministic tests.

### P2 — `provenance_binding: true` covers only two fields

`environment/audit.py:110-117` compares `snapshot_sha256` and `project.project_id`; it does not bind
the rest of `PROVENANCE.json`, including the license boundary, source commit metadata, upstream
reference, and `linked_content_copied` assertion. The current file's SHA-256 matches the builder's
record, but that record is prose evidence rather than an authoritative integrity check.

Either bind the complete canonical provenance object/file from the manifest or rename the audit
result to the narrower property it actually checks. Keep the source-snapshot identifier distinct
from a provenance-file digest.

### P3 — Clarify two learner-facing contract claims

- `REQUIREMENTS.md:17-19,46-52` gives a length and reserved-name rules but does not say whether an
  integer-shaped token may be a definition name. The reference rejects `: 123 7 ;` with status 2.
  State that rule explicitly so a contract-following learner and validator cannot diverge.
- `README.md:33-34` says a “build-sanity test” passes immediately, but the public suite contains no
  such test; all its methods launch the deliberately failing stub. Call this a build command, or add
  the promised deterministic sanity test.

## Verified strengths

- The manifest is conservative: `GENERATED` and `PARTIAL` only, `productionized: false`, and
  independent validation required. It does not claim build, test, fuzz, benchmark, review,
  transfer, or production labels.
- Direct GNU assembly/linking succeeded. The reference is static ELF64 x86-64, exports `_start`,
  and has a writable/non-executable GNU stack.
- Public tests passed 10/10, sealed reference tests passed 13/13, and the independent harness
  passed all 46 assertions, including seeded arithmetic properties and resource edges.
- The learner surface has a clear contract, progression, concepts, review questions, and a minimal
  starter without a reference implementation. Benchmark output is explicitly labeled
  `UNVALIDATED_MEASUREMENT`.
- The candidate audit reproduced its recorded output, all seven recorded content hashes matched,
  all five Python files compiled in memory, and both JSON documents parsed.

## Review limitations

The upstream immutable snapshot was not present, so the CC0 catalog assertion, linked-resource
license, and clean-room/non-copying claim could not be authenticated independently. The reviewer
workspace intentionally exposes the sealed tree as read-only; whether a real learner view excludes
it is an external control-plane property and was not transfer-verified. Native linking used the
available system binutils because no pinned x86-64 binutils root was configured.

