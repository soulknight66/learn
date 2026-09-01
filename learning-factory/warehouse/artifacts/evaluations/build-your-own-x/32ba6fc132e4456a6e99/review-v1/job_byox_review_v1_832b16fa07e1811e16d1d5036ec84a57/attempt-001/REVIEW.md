# Independent review

Verdict: **REVISE**. The learning design and static reference logic are coherent, and the
`GENERATED` + `PARTIAL` labels are appropriately conservative. The candidate is not ready for
learner transfer or stronger validation labels because isolation, contract, and artifact-integrity
gaps remain.

`CANDIDATE/` was treated as immutable. Its aggregate fingerprint was unchanged after review.

## Prioritized findings

### P1 — No enforceable learner/sealed boundary is demonstrated

The complete solution, reference tests, and answer keys are present as ordinary readable files.
For example, `sealed/reference/README.md:3-5` says the reference must not enter a learner view, and
`adversarial/README.md:3-4` says its answer key must remain hidden. Nevertheless, every candidate
file is mode `0444`; `README.md:77` and `AGENTS.md:3-5` supply only “do not inspect” prose. No
allowlisted learner-view manifest, exporter, ACL test, or transfer evidence is included.

If the whole candidate tree is mounted for a learner, assessment answers and hidden scenarios leak
immediately. If an external harness projects a safe view, that dependency remains unverified here.
Before release, construct the learner view from an explicit allowlist and validate that every
`sealed/` subtree and nested `*/sealed/` answer key is absent.

### P1 — The structural verifier passes a materially incomplete artifact

`sealed/validation/verify_artifact.py:18-42` requires 23 documentation paths but no Java source,
test source, or runner. Its lexical check at lines 119-142 validates only Java files that happen to
be discovered, while lines 67-71 fingerprint only `MANIFEST.yaml` and `PROVENANCE.json`.

An independent mutation check copied the candidate to reviewer scratch space, removed all eight
Java files and both `run.sh` files, and ran the unmodified verifier. It exited `0` and printed:

```text
PASS required regular files: 23
...
PASS Java lexical structure: 0 source files
```

Thus the validator neither proves completeness nor binds the generated implementation, tests, and
documentation to a reviewed artifact. Require every core path, reject unexpected/missing inventory
entries, assert the expected source count, and record per-file digests or an equivalent deterministic
artifact manifest.

### P1 — The declared authoritative contract is weaker than the tests

`README.md:14-19` says `REQUIREMENTS.md` defines observable behavior, and
`public_tests/README.md:17-18` calls it authoritative. Public tests nevertheless enforce behavior
specified only in supplementary `starter/README.md`:

- `ContractTests.java:69-72` rejects a negative `LogRecord` offset, but
  `REQUIREMENTS.md:20-26` specifies non-negative partition and replica IDs, not record offsets.
- `ContractTests.java:105-110` requires the numerically lowest initial leader, while
  `REQUIREMENTS.md:40-41` requires only a deterministic initial choice.
- `ContractTests.java:176-184` requires `leaderId()` to throw `IllegalStateException` without a
  leader; the authoritative API contract does not define that result.
- The same test requires safe recovery to restore leadership. `REQUIREMENTS.md:61-64` says such a
  recovery “may” seed an election rather than requiring it.

Also, sealed tests at `ReferenceTests.java:65-75`, `97-104`, and `106-113` require collection
mutations to throw `UnsupportedOperationException`. The requirements only demand detached/stable
snapshots that cannot mutate internal state (`REQUIREMENTS.md:24`, `36`, and `51`); a mutable copy
satisfies that wording. The sealed suite currently targets the fixed reference, but it must not be
reused unchanged as a general learner validator.

Consolidate every externally tested behavior in the authoritative contract, or relax tests to the
published contract.

### P2 — Progressive disclosure is descriptive, not executable

`README.md:22-23` tells learners to advance after each public-test “group” passes, and line 18 says
`starter/README.md` maps milestones to source files. In practice, `starter/README.md:12-65` exposes
the full behavior and has no milestone mapping. `public_tests/run.sh:20` always launches one suite;
`ContractTests.java:15-26` executes all ten cases with no group selector or per-milestone pass
report.

Provide milestone-specific commands/filtering and a real file/task map, or remove the claim that
test-group completion gates disclosure.

### P2 — Reproduction prerequisites are incomplete

`README.md:57-65` and `environment/README.md:6-9` describe only a JDK and POSIX shell. Both runners
also depend on `mktemp` (not a POSIX utility), supporting path utilities, and a writable
`${TMPDIR:-/tmp}` (`public_tests/run.sh:4-10`; the sealed runner is equivalent). On this host the
documented commands stopped before compilation because `/tmp` does not exist. Setting `TMPDIR` to
the reviewer workspace let both reach `javac`, which is unavailable.

The required independent-verification command also needs a compatible Python, but no Python
version appears in the environment guide. PATH `python3` is 3.6.8 and fails on
`verify_artifact.py:4`; Python 3.11.5 runs it. Document all prerequisites, validate them up front,
and offer a controlled temporary-directory override.

### P2 — Generated material has no explicit license grant

The catalog snapshot is identified as CC0 and linked material is candidly `NOASSERTION`.
`LICENSE_BOUNDARY.md:8-10`, however, only says newly generated material is “intended for personal
educational use.” There is no `LICENSE`, `COPYING`, `NOTICE`, or SPDX grant governing reuse,
modification, or redistribution of the generated challenge. Add explicit terms or state clearly
that no license is granted and constrain transfer accordingly.

### P3 — Provenance and coverage descriptions need precision

- `MANIFEST.yaml:5` labels a value `provenance_sha256`; it equals
  `PROVENANCE.json:50`'s `snapshot_sha256` but neither the raw provenance-file digest nor its
  canonical-object digest. No included schema defines the field. Clarify that it identifies the
  source snapshot, or bind it to the provenance artifact it names.
- Provenance records the source catalog and commit but not the generator/model/prompt/configuration
  or per-file lineage. `PROVENANCE.json:78` also embeds a nonportable internal user path.
- `sealed/reference_tests/README.md:5-7` calls its coverage a long transition trace. The sole trace
  at `ReferenceTests.java:228-255` is a fixed sequence of about 13 state-changing calls and five
  appends. `VALIDATION.md:128-134` correctly leaves long generated traces to future validation, so
  the suite description should be narrowed.

## Positive evidence

- Manifest status is `GENERATED`, labels are exactly `GENERATED` and `PARTIAL`, and
  `productionized` is false. No positive high-assurance validation label is claimed.
- The candidate has 38 regular files, no symlinks, no archived Java products, and only Java
  standard-library imports. The Python 3.11 structural scan found no high-confidence credential
  pattern.
- Static review found the reference append, commit visibility, deterministic failover, stale-first
  recovery, defensive-copy, and idempotence logic internally coherent for states reachable through
  the public API.
- Production limitations, benchmark non-results, and the distinction between minimum ISR and real
  consensus are stated unusually clearly.

These positives are not build or test evidence. No manifest or validation label was changed.
