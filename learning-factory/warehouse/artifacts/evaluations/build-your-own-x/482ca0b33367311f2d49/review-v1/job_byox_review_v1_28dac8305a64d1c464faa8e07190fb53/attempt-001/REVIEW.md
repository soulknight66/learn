# Independent review

## Disposition

**REVISE.** The pack is unusually candid about its partial status and has useful staged material, but the reference violates several explicit contracts and the primary learner command is not runnable as written in the supplied environment. Passing the submitted suites is narrow evidence only; it does not promote any validation label.

## Prioritized findings

### P1 — non-finite values disable the execution bound

`CANDIDATE/sealed/reference/minibox/runtime.py:110` rejects values only when `timeout <= 0`. Both `NaN` and positive infinity pass that check, and `CANDIDATE/sealed/reference/minibox/cli.py:49` accepts both through `type=float`. Independent probes confirmed that `Runner(..., timeout=float("nan"))`, `Runner(..., timeout=float("inf"))`, and CLI values `--timeout nan|inf` are accepted. Infinity is not a bounded timeout, contradicting R6.

Require a finite positive value (for example, with `math.isfinite`) in the runner and add deterministic constructor and CLI tests.

### P1 — one launch failure leaves durable state stuck at RUNNING

The runner claims `RUNNING` before `Popen`, but `CANDIDATE/sealed/reference/minibox/runtime.py:143` handles only `OSError`. A custom backend satisfying the current tuple-of-strings check returned a NUL-bearing argument; `Popen` raised `ValueError`, which escaped while state and events remained `CREATED -> RUNNING`. This contradicts R6's requirement that launch failure record `FAILED` and surface a domain error.

Validate every backend argument as non-empty and NUL-free before claiming, and make post-claim launch exception handling restore a durable terminal state. Cover the exact state/event history in a test.

### P1 — the advertised learner command selects Python 3.6

`CANDIDATE/README.md:22`, `CANDIDATE/AGENTS.md`, and the subordinate guides tell learners to invoke `python3`. In this allocated workspace that is Python 3.6.8, while no `python3.11` command is on `PATH`. The exact learner command exits 1 with five discovery-time `from __future__ import annotations` errors, before reaching the intentional starter failures. The reference succeeds only with `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`.

Provide a portable, checked Python 3.11 launcher/environment and use it consistently in every copy-paste command. A clear version statement elsewhere does not make the primary command executable.

### P2 — R1 accepts nondeterministic argv containers

R1 requires a tuple/list, but `CANDIDATE/sealed/reference/minibox/models.py:67` converts any iterable with `tuple(self.argv)`. Sets and generators were accepted. The same set serialized in three subprocesses produced three different argument orders under hash seeds 1, 2, and 3, violating canonical/reproducible serialization and potentially changing the executed command.

Reject inputs outside the documented tuple/list types and add set, generator, mapping, and mutation tests.

### P2 — an image manifest can identify bytes that were not applied

`Workspace.import_image` applies the caller's path at `CANDIDATE/sealed/reference/minibox/workspace.py:73` and opens that path again for hashing at line 76. A controlled replacement between those operations yielded extracted payload `applied-A` while `layer_sha256` matched replacement B. This weakens the manifest's provenance and reproducibility evidence.

Copy and hash the input into an owned immutable staging file, then apply that same file. The sealed content-addressed-store sketch already describes the appropriate boundary.

### P3 — public feedback omits two major milestones

The public runtime tests cover only argv planning, not `Runner`; there is no public CLI test. All runner and CLI feedback is sealed even though R6 and R7 are substantial learner milestones and `public_tests/README.md` calls its cases representative. Add small public happy-path/error cases while retaining adversarial variants for independent validation.

## Positive evidence

- With Python 3.11.5, independent execution observed 18/18 public, 22/22 sealed, and 4/4 adversarial tests pass.
- Archive tests cover preflight rejection, traversal, links, whiteouts, special files, limits, and existing symlinks. State tests cover the transition graph, trigger enforcement, history, monotonic timestamps, and a two-claimant race.
- SQL is parameterized, lifecycle claims use `BEGIN IMMEDIATE`, and the schema enforces the transition graph. No unsafe tar extraction helper or `shell=True` call site was found.
- The learning path, requirements, concepts, questions, debugging exercises, tradeoffs, alternatives, and production gaps are clearly separated. All three answer files and the implementation reference are under `sealed/`.
- `MANIFEST.yaml` and `PROVENANCE.json` agree on project/source/snapshot identifiers. The catalog/linked-resource boundary is explicit, and the overall artifact makes no production, fuzz, benchmark, or full-isolation claim.

## Residual limitations

- The namespace probe validates only rootless user-namespace availability. No full MiniBox payload or populated rootfs was exercised.
- Actual learner-view filtering and transfer isolation could not be tested from this all-material reviewer workspace.
- The linked repository was unavailable and `git` was not installed, so independent no-copy/license comparison was impossible. `NOASSERTION` for the linked resource is appropriately retained.
- No fuzzing, benchmark, production, crash-recovery, or hostile concurrent-rootfs campaign was run. The submitted status should remain `GENERATED` + `PARTIAL`.
