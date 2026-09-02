# Independent review

Verdict: **REVISE**

The pack is thoughtfully scoped and unusually candid about its non-goals, but two reference-contract
defects and two release/evidence defects prevent an advisory pass. `CANDIDATE/` was treated as
immutable throughout this review.

## Prioritized findings

### 1. High — an invalid derived whiteout target mutates the destination before rejection

`REQUIREMENTS.md:27-41` requires full preflight and an unchanged destination on preflight failure.
The header parser accepts `.wh...` as a regular whiteout marker, whose derived target is `..`.
`sealed/reference/pydocklet/layer.py:207-213` simulates that target without passing it through the
safe-path grammar. Only during application does `resolve_beneath` reject it at lines 267-273.

An independent regression used a layer ordered as `.wh.victim`, then `.wh...`. It observed:

```text
exception=PathEscape victim_exists=False
```

The escape is blocked, but the earlier valid whiteout has already destroyed lower-layer data. This
also falsifies the broad no-whiteout-before-deterministic-rejection invariant stated in
`sealed/DESIGN.md:89-90`.

Required revision: derive and validate every whiteout target during header preflight, retain the
validated target in the entry model, and add a regression proving that a later invalid marker cannot
allow an earlier whiteout to mutate the destination.

### 2. High — the prescribed learner export strips the terms it is required to preserve

`LICENSE_BOUNDARY.md:10-16` grants the generated-material permissions only with a direction to
preserve both `PROVENANCE.json` and the boundary notice with a copy. The prescribed learner exporter
deliberately omits both (`README.md:71-74` and the 27-path allowlist). A real export confirmed there
was no license/provenance-named file and no explicit generated-material grant anywhere in the learner
tree.

This is not a sealed-content leak—the allowlist correctly excludes evaluator material—but it leaves
the intended recipient without the permission terms and makes the supported export contradict the
notice's preservation condition.

Required revision: include a learner-safe license/provenance notice carrying the applicable grant and
source boundary, or explicitly define an export exception while ensuring recipients still receive
the operative terms. Do not expose sealed tests or answers to solve this.

### 3. Medium — implicit directory modes depend on the caller's umask

`REQUIREMENTS.md:33` requires directories to be normalized to `0755`. The implementation supplies
`mode=0o755` to `mkdir` at `layer.py:254,316,329`, but only explicitly listed tar directories are
later forced to `0755` at lines 336-337. Under umask `077`, a layer containing only
`implicit/file` produced:

```text
root_mode=0o700 implicit_mode=0o700
```

Required revision: explicitly chmod every created directory that belongs to the materialized layer
(including the destination and implicit parents), and add a restrictive-umask regression.

### 4. Medium — the recorded validation recipe omits a required scratch precondition

`VALIDATION.md:46-56` creates and then deletes `environment/.validation-tmp`. Later suite commands
still set `TMPDIR=environment/.validation-tmp` (`VALIDATION.md:83-88` and subsequent sections) without
recreating it. With the directory absent in the immutable artifact, the configured CPython reported:

```text
FileNotFoundError: [Errno 2] No usable temporary directory found in
['environment/.validation-tmp', '/tmp', '/var/tmp', '/usr/tmp', '.../CANDIDATE']
```

The supplied pass results are plausible when scratch exists, and this review reproduced them using
scratch outside `CANDIDATE`; however, the command sequence as recorded is not self-contained.

Required revision: keep scratch until every suite completes or create/remove it within each command
section, then regenerate the observed validation log from that exact sequence.

## Positive evidence

- The configured CPython 3.11.5 compiled all Python material successfully.
- The public reference suite passed 11/11 and the sealed suite passed 34/34. The untouched starter
  failed with the documented 17 explicit TODO errors.
- A real learner export contained exactly the 27 allowlisted files, matched source bytes, contained no
  evaluator root, and passed its own boundary check. Progressive disclosure is otherwise clear and
  useful.
- The documentation prominently says this is not a security boundary and accurately disclaims fuzz,
  benchmark, transfer, production, namespace, disk-quota, decompression-budget, crash-reconciliation,
  and schema-evolution evidence.
- The manifest remains `GENERATED` + `PARTIAL`, requires independent validation, and does not claim
  productionization. No forbidden promotion was made.
- Static scans found no `extract`/`extractall`, `shell=True`, common credential signature, nonregular
  candidate entry, bytecode cache, or validation scratch residue.
- The candidate's 59-file inventory digest remained unchanged across review.

## Review limitations

The external factory inventory and upstream source snapshot were unavailable, and network access was
restricted. Accordingly, source-similarity, upstream-license, baseline-identifier, and remediation-
identifier assertions remain unverified. This review also did not perform fuzzing, benchmarking,
hostile execution, cross-host transfer validation, or production security assessment.

An eventual PASS would remain advisory; only the orchestrator-controlled acceptance validator can
publish a `REVIEWED` label.
