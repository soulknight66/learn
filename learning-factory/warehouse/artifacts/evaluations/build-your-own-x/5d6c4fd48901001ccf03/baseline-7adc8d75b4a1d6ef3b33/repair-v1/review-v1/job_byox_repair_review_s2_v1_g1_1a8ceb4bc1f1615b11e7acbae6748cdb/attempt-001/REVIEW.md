# Independent review

Verdict: **REVISE**. The core workshop material is promising and most builder results reproduce,
but the submitted evidence transcript and learner-disclosure boundary are not acceptable as-is.

## Prioritized findings

1. **High — the claimed exact validation commands are not replayable.**

   `CANDIDATE/VALIDATION.md` lines 52, 61, 72, 78, 86, 97, 168, 178, 186, and 196 contain literal
   `+` tokens between command arguments. Replaying line 52 verbatim exited 127 with
   `/usr/bin/env: ‘+’: No such file or directory`, despite the adjacent claim of exit 0. Removing
   those tokens made the independently run suites reproduce the reported test counts. Replace the
   transcript with the commands actually executed and rerun them from a clean workspace; claimed
   observations must correspond byte-for-byte to executable commands.

2. **High — progressive disclosure is an honor-system instruction, not an isolation boundary.**

   The submitted tree directly exposes `sealed/reference/`, `sealed/reference_tests/`, design and
   production answers, exercise answer files, and adversarial tests. `CANDIDATE/AGENTS.md:3` tells
   learners not to read them, while `CANDIDATE/sealed/reference/README.md:3` and
   `CANDIDATE/adversarial/README.md:3` claim they are not learner-visible. The only pack verifier
   actively requires several sealed paths (`CANDIDATE/environment/verify_pack.py:18`). Supply
   separate learner and instructor artifacts, or a deterministic export step with independent
   manifests proving that no reference, answer, adversarial, or hidden evaluator content enters the
   learner view.

3. **Medium — the safe default execution path is not usable on the supplied host.**

   `readonly_root` defaults to true (`sealed/reference/minictr/spec.py:85`), but the provided kernel
   integration test explicitly sets it false (`sealed/reference_tests/test_linux_integration.py:42`).
   The writable smoke passed; an otherwise identical true-mode smoke returned child exit 126 with
   `PermissionError: [Errno 1] Operation not permitted` at the remount target. The builder honestly
   discloses that read-only remounting was not established. Add a deterministic capability check and
   actionable unsupported-host result, or implement and test a compatible read-only setup so the
   default does not fail only after launch.

4. **Medium — pack verification does not bind the generated implementation.**

   The verifier checks 24 named documentation/metadata paths and the exact provenance document, but
   its required inventory omits all `starter/minictr/*.py`, reference implementation files, and test
   files. Those can be changed or removed without violating the declared provenance digest, which is
   explicitly a source-snapshot identifier rather than an artifact digest. Add a canonical complete
   file inventory with per-file digests for each learner/instructor artifact and validate it.

## What held up

- The configured Python 3.11.5 interpreter worked. Corrected commands produced 10 passing starter
  public tests, the documented initial-red checkpoint result, 4 passing reference checkpoints, 29
  reference tests with one opt-in skip, and 4 passing adversarial tests.
- The supplied writable-root Linux smoke passed, and the host probe accurately limited its claim to
  basic user-namespace availability.
- Static review confirmed parameterized SQLite, explicit transactions, `BEGIN IMMEDIATE`, a
  database-enforced transition trigger, argv-based launch, bounded input, a fresh process session,
  and process-group timeout cleanup.
- The learner route, initial-green/opt-in-red staging, threat-model discussion, and production gaps
  are unusually clear. The manifest is appropriately conservative: `GENERATED`, `PARTIAL`,
  `productionized: false`, and independent validation required.
- The internal provenance digest is consistent. The license text correctly avoids treating the
  linked `NOASSERTION` tutorial as reusable source material, although the external no-copy and
  upstream-license assertions could not be independently checked in this restricted workspace.

No candidate file or manifest was changed, and this review does not confer `REVIEWED`.
