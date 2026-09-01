# Independent review

Verdict: **REVISE**.

The candidate is unusually candid about its educational scope, and its reference
implementation passes both bundled deterministic suites. It is not ready for
promotion, however: independent fault injection found a direct contradiction of
the persistence contract, and the submitted artifact does not itself enforce the
claimed boundary between learner material and sealed answers. The candidate
manifest was not modified.

## Prioritized findings

### P1 — A failed state operation can publish the state it reports as failed

`CANDIDATE/REQUIREMENTS.md:226-230` promises that failed operations do not
publish a new revision. The reference publishes before its final directory sync:

- creation links the visible record at
  `CANDIDATE/sealed/reference/minibox/state.py:264`, then syncs the directory at
  line 283;
- transition replaces the visible record at line 307, then syncs the directory
  at line 309 and propagates an error at lines 310-311.

An independent injected `_sync_directory` failure produced:

```text
{'transition_before': ('CREATED', 0),
 'transition_error': 'injected directory sync failure',
 'transition_after': ('RUNNING', 1),
 'create_error': 'injected directory sync failure',
 'create_after': ('CREATED', 0)}
```

Atomic visibility still holds—the records are complete—but API failure no
longer means “not published.” The available failure regression only injects a
write error before publication
(`CANDIDATE/sealed/reference_tests/test_reference_state.py:249-260`). Revise the
contract to model an indeterminate post-publication durability outcome and add a
recovery protocol, or change the implementation and validation so its stated
semantics are true.

### P1 — Sealed material is separated by prose, not by the submitted artifact

`CANDIDATE/AGENTS.md:9-18` and `CANDIDATE/README.md:82-87` tell learners not to
inspect `sealed/`, but the submitted tree contains readable reference code,
validator tests, debugging answers, and review-exercise answers. Independent
`test -r` checks succeeded for both a reference source file and an answer file.
`CANDIDATE/MANIFEST.yaml` has no student-view path allowlist or separately hashed
learner artifact.

If the factory has an external deterministic view filter, that control was not
present or verifiable here. If `CANDIDATE/` is delivered as-is, progressive
disclosure fails and answers/hidden checks are exposed. Produce and validate a
separate learner artifact, or add a machine-enforced allowlist whose output is
hashed and checked for all `sealed/` paths.

### P1 — The advertised learner-validation suite exceeds the learner contract

`CANDIDATE/sealed/reference_tests/README.md:14-18` says the sealed suite can be
pointed at a learner implementation. Several checks are not safe conformance
tests for the normative contract:

- `CANDIDATE/REQUIREMENTS.md:329-332` explicitly lets learners choose CLI/helper
  details, while `test_reference_child.py:15-28,59-79` calls private `_payload`
  and `_status_descriptor` APIs and requires `MINIBOX_STATUS_FD`;
- `test_reference_cli.py:30-72` requires undocumented `check`/`plan` output;
- `test_reference_config.py:78-91` rejects a symlink in the configured rootfs
  path although the learner contract only specifies an absolute existing
  directory and symlink checks below the rootfs;
- `test_reference_config.py:219-240` requires duplicate-key rejection without
  stating that policy in `REQUIREMENTS.md`.

Keep implementation-specific self-tests for the reference, but use only
learner-visible requirements for learner validation. Alternatively, make every
graded behavior normative and visible.

### P2 — Provenance does not integrity-bind the submitted artifact

`CANDIDATE/MANIFEST.yaml:5` records
`f7a36c6e…` as `provenance_sha256`, and
`CANDIDATE/PROVENANCE.json:50` repeats it as `snapshot_sha256`. The actual
SHA-256 of the submitted `PROVENANCE.json` bytes is
`61d0f204e6e3a1e7647e3b6eed3a918b3a6b30ede1056213767ed030629a3cdc`.
If the manifest field is meant to identify a catalog snapshot instead of the
provenance document, that meaning and canonicalization are not defined in the
artifact.

The record captures useful catalog IDs, commit/tree metadata, and extractor
version, but not a generation recipe, generator/model identity, run ID,
per-file hashes, or a Merkle/inventory hash for the 65 submitted files. It
therefore cannot reproduce the pack or detect substitution of generated files.
Add explicit hash semantics and a generated-artifact inventory tied to the
manifest.

### P2 — Rights for generated material remain ambiguous

The upstream boundary is handled well:
`CANDIDATE/LICENSE_BOUNDARY.md:7-23` consistently treats the catalog as CC0 and
the linked tutorial as `NOASSERTION`, and does not claim permission to copy the
linked work. However, “independently generated for personal educational use” is
not an explicit license grant. There is no LICENSE/COPYING/NOTICE file or SPDX
declaration covering the challenge prose, tests, and reference code. State the
copyright holder and redistribution/modification terms. Independent authorship
and non-copying could not be verified without the upstream snapshot.

### P2 — The live probe overstates what its `/proc` predicate proves

`CANDIDATE/environment/live_payload.c:12` only checks whether
`/proc/self/status` is readable. The same predicate was true in an ordinary
review process (`pid=2`), so that field alone cannot distinguish a fresh procfs
view. PID 1 and the configured hostname are useful evidence for PID/UTS setup,
but `CANDIDATE/VALIDATION.md:95-97` goes further by calling the result a new proc
view. Check namespace inode differences, mount metadata, and visible PID
contents in a disposable integration runner before making that claim.

### P3 — Staging and environment setup can be clearer for learners

The learning order is sensible, but the only documented test command runs all
stages. The untouched starter emits 32 error tracebacks, and later plan/runtime
tests depend on stage-one `from_dict`. Add per-stage commands or a staged runner.
Also route the main learning path to `adversarial/`, `debugging/`,
`review_exercises/`, and `benchmarks/`, and state whether those submissions and
the Linux extension are required for completion.

The documented commands assume `python3` is at least 3.10. In this review
workspace it is 3.6.8; an explicitly located Python 3.11.5 worked. A version
preflight and captured interpreter/tool versions would make the instructions
more reproducible.

## Evidence that did hold up

- Under explicit Python 3.11.5, the reference passed all 24 public tests and all
  65 sealed tests. The untouched starter reproduced the documented 24-test,
  32-error baseline.
- All 35 generated Python files parsed successfully.
- Both metadata documents strict-parsed as JSON; project, source, and commit
  cross-references agree.
- The candidate has 65 regular files, no symlinks or special files, and no hits
  in the bounded obvious-credential pattern scan.
- Passive and active namespace probes reproduced the recorded kernel/Python
  facts and a successful narrow user-namespace operation.
- A separate bounded live run with a disposable rootfs and the benign host
  `true` binary completed setup/exec and recorded `EXITED` revision 2. It did
  not instrument PID, UTS, or proc behavior.
- Safety language is strong and consistent. The candidate repeatedly says that
  plans and mocked tests do not prove isolation, rejects production use, lists
  missing controls, and keeps the manifest at `GENERATED`/`PARTIAL` with
  independent validation required.

Passing the bundled suites is useful evidence, but it does not erase the
independently demonstrated contract failure or justify any validation-label
promotion.
