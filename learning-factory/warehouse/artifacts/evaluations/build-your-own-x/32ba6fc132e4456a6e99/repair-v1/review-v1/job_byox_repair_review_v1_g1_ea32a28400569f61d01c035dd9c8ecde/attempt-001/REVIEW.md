# Independent review

## Advisory verdict: REVISE

The pack is candidly labeled `GENERATED + PARTIAL`, and its bounded in-process design is generally
clear. It is not ready for an advisory pass: the staged learning workflow contradicts its public
tests, the authoritative contract does not specify one behavior that the tests require, the exact
learner export breaks its own provenance/license links, and no Java source could be compiled or run.
This verdict does not publish `REVIEWED`; only an orchestrator-captured acceptance validator may do
that.

## Prioritized findings

### P1 — Milestone selectors require later-milestone work

`README.md:41-53` assigns failure/election to milestone 3 and recovery to milestone 4.
`public_tests/README.md:13-23` says the groups are independent and that an unfinished later
milestone cannot obscure the selected result. The suite contradicts those promises:

- The milestone-2 configuration case calls `failReplica`, `recoverReplica`,
  `isReplicaAvailable`, and `replicaEndOffset` (`ContractTests.java:130-134`), although failure and
  recovery are introduced later.
- The milestone-3 failover case performs recovery and catch-up (`ContractTests.java:180-184`).
- The milestone-3 no-leader case calls `recoverReplica` twice and requires leadership restoration
  (`ContractTests.java:208-216`).

A learner who correctly leaves milestone-4 recovery unimplemented cannot pass milestone 3; even
milestone 2 requires partial later APIs. Move these assertions into their owning groups or redefine
the milestone contract consistently in every learner-facing document.

### P1 — The authoritative contract permits implementations that the public suite rejects

The root README and public-test README both identify `REQUIREMENTS.md` as authoritative.
`REQUIREMENTS.md:40-41` requires only “a deterministic initial leader.” A deterministic choice such
as the highest configured ID therefore conforms. Yet `starter/README.md:43` and
`ContractTests.java:138-142` require the lowest ID. State the lowest-ID rule in the authoritative
requirements, or relax the assertion. Learners should not have to infer a tested rule from a
secondary file that is nominally subordinate to the contract.

### P1 — The exact learner export omits the documents that grant and explain its boundary

The exported `README.md:77-78,91-92` links to `VALIDATION.md`, `PROVENANCE.json`, and
`LICENSE_BOUNDARY.md`. None is present in the exact 15-file allowlist. The resulting learner view
has three dead references and, more importantly, omits the only explicit CC0 grant and explanation
of the linked resource's `NOASSERTION` boundary. A temporary export reproduced this exact state and
still passed `verify_student_view.py`, because the omission is encoded as the expected inventory.

Provide a learner-safe license/provenance notice and make the README self-contained, or include safe
versions of the referenced documents in the allowlist. Do not expose the internal absolute source
path merely to repair the link; a sanitized provenance summary is sufficient.

### P1 — Required executable correctness evidence is still absent

With an external writable `TMPDIR`, both runners progressed to `javac` and then exited 127 because
neither `javac` nor `java` exists on this host. Thus the proposed reference has not been compiled
with `--release 17 -Xlint:all -Werror`, and none of the 10 public or 14 sealed cases—including the
1,024-operation fixed-seed model trace—ran. Static inspection found no obvious reachable-state
contract violation, but it cannot substitute for compilation or behavioral validation. Run both
runners on a JDK 17+ acceptance host and preserve harness-captured logs before considering a pass.

## Positive observations

- Validation claims are appropriately restrained: the manifest says `PARTIAL`, `productionized` is
  false, and the prose explicitly disclaims build, test, fuzz, benchmark, review, transfer, and
  production labels.
- Manifest project, source, commit, and snapshot identifiers agree with the provenance object. The
  full-pack license document clearly separates independently generated CC0 material from the linked
  `NOASSERTION` resource and addresses the Kafka trademark boundary.
- The reference design is deterministic and focused. Public and sealed sources cover ownership,
  boundaries, atomic rejection, failover, stale-first recovery, idempotence, and a fixed-seed state
  model. All Java imports are standard-library imports.
- The structural validator, runner syntax, scratch cleanup, exact-inventory learner validator, and
  invalid-`TMPDIR` failure path behaved as documented in the checks available here.

## Scope and limitations

`CANDIDATE/` was inspected read-only and retained its 40-file aggregate hash. The linked tutorial
could not be fetched or compared because git and external source access are unavailable, so the
pack's no-copy provenance assertion remains uncorroborated. The reviewer-created learner view was a
useful inventory test but is not an orchestrator delivery and therefore does not establish
`TRANSFER_VERIFIED`.
