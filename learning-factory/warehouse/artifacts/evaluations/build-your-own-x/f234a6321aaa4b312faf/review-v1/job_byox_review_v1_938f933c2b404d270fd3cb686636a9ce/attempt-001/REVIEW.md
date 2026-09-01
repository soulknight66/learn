# Independent review

Verdict: **REVISE**. The pack is unusually candid about its partial status and has a strong teaching
shape, but the sealed reference has a fail-open internal entry path, one parser/contract mismatch,
and no executable Go evidence. Keep every current validation label unchanged.

## Prioritized findings

### P1 — High: the internal child mode does not establish that namespace cloning happened

The CLI dispatches any first argument equal to `__tinycontainer_init` directly to
`RunChildInvocation` ([main.go](CANDIDATE/sealed/reference/cmd/tinycontainer/main.go#L12)). The child
path merely searches argv for the literal `--error-fd=3`, calls a no-result `CloseOnExec(3)`, parses
the same fixed integer, and proceeds to `enterAndExec`
([runtime.go](CANDIDATE/sealed/reference/runtime.go#L82),
[arguments.go](CANDIDATE/sealed/reference/arguments.go#L90)). It never checks that descriptor 3 is
open and is the expected inherited channel, nor that the process entered the planned namespaces.

A direct invocation can therefore skip `BuildLaunchPlan` and all clone flags. For an unprivileged
caller, the first mount will normally fail; for a privileged operator, the subsequent recursive
mount-propagation change, bind mount, hostname change, and proc mount run in the caller's current
mount/UTS namespaces ([runtime_linux.go](CANDIDATE/sealed/reference/runtime_linux.go#L42)). This
contradicts R10's fresh-namespace invariant and makes the statement that re-exec supplies an
"authenticated parent-child relationship" ([TRADEOFFS.md](CANDIDATE/sealed/TRADEOFFS.md#L31))
stronger than the code supports.

Make the internal entry fail closed before its first side effect: validate an inherited control
channel/handshake and relevant namespace preconditions, and add a subprocess test proving that a
direct marker invocation with a missing or wrong channel performs no setup call. Continue to treat
the binary as unsuitable for hostile workloads even after that correction.

### P1 — High: the Go deliverable has never been compiled or executed

There is no builder or reviewer evidence that either starter or reference compiles under Go 1.21,
that the tests compile, or that build tags work off Linux. Every independent Go attempt exited 127
because this host has no Go executable. Static reading is not a substitute for `go build`, `go vet`,
`gofmt`, or tests. The candidate states this accurately, but it remains a release blocker for a Go
learning pack.

Run independent CI with a pinned supported Go toolchain over every module. At minimum, record
`gofmt -d`, `go vet`, starter/reference builds, public/reference/adversarial/debug tests, the race
detector where supported, and non-Linux compile checks. Keep the integration tier isolated and
opt-in.

### P2 — Medium: `ParseRunArgs` accepts a command without the required `--`

R7 says the command occurs after `--`. The implementation delegates directly to
`flag.FlagSet.Parse` and assigns all residual arguments to `cfg.Command`
([arguments.go](CANDIDATE/sealed/reference/arguments.go#L61)). Go's flag parser also stops at the
first non-flag, so an invocation shaped like `run --rootfs PATH /bin/probe` is accepted even though
the separator is absent. All submitted positive tests include `--`; none checks its absence.

Track the separator explicitly (or use a small deterministic parser) and add rejection tests for a
missing separator, misplaced flags, internal-only flags, and malformed boolean values.

### P2 — Medium: progressive disclosure is organized but not transfer-verified

The documented learner allowlist is sensible, and no solution path is nested under `starter/`,
`public_tests/`, or `environment/`. However, this submitted tree has 25 readable files beneath a
`sealed` path component, including the complete reference and exercise answers. The submitted
verifier checks only that certain path component names do not occur inside three visible roots
([verify-pack.py](CANDIDATE/environment/verify-pack.py#L140)); its
`learner_solution_paths=PASS` output does not inspect an independently produced student view.

This is not an observed student leak—the review workspace is expected to expose sealed material—and
the manifest correctly avoids `TRANSFER_VERIFIED`. Before learner delivery, have the deterministic
harness construct an explicit allowlisted view, then independently assert that no sealed,
adversarial, benchmark, debugging-answer, or review-answer file or content hash is reachable there.

### P2 — Medium: learner and reference tests leave important deterministic behavior uncovered

The public suite gives useful feedback on defaults, a few validation cases, child round-tripping,
and clone planning. It does not cover much of the stated deterministic contract, including all
hostname/environment boundaries, mandatory CLI grammar, empty-environment semantics, negative IDs,
or plan path errors. Reference tests add some of these, but still have no injected unit coverage for
the setup-error pipe, cancellation races, direct internal dispatch, setup-versus-workload status,
or signal conversion. The one integration test covers a happy probe and ordinary exit 17 only—and
has never run here.

Add deterministic failure-injection tests around process launch and the child protocol, as the
sealed design notes already recommend. Keep public tests incomplete enough for assessment, but give
learners feedback across each pure requirement family.

### P2 — Medium: generated-material reuse rights are not defined

The boundary correctly preserves `NOASSERTION` for the linked InfoQ resource and does not imply that
the catalog's CC0 status licenses linked content. However, "supplied for personal educational use"
([LICENSE_BOUNDARY.md](CANDIDATE/LICENSE_BOUNDARY.md#L7)) is not a standard license or a precise
grant for the independently generated prose/code/tests. Redistribution, modification, and classroom
use are therefore unclear. Add an explicit license or clearly stated terms for generated material,
while retaining the linked-resource boundary. Consider removing the internal absolute source path
from learner-visible provenance unless it is operationally required.

### P3 — Low: the static fixture build is not failure-atomic

`make-rootfs.sh` creates `bin/` and `proc/` before invoking the static compiler
([make-rootfs.sh](CANDIDATE/environment/make-rootfs.sh#L31)). The independently reproduced missing
`-lc` failure left those directories behind; the same target then fails the script's nonempty-target
precondition. The documentation discloses both the static dependency and non-deletion behavior, so
this is a reproducibility nuisance rather than a hidden claim. Compile in a controlled sibling
scratch location and populate the target only after success, or document an exact safe retry cleanup.

## Evidence that held up

- Manifest labels and claim language are conservative and consistent: `GENERATED`, `PARTIAL`,
  independent validation required, and `productionized: false`.
- Manifest/provenance identifiers and canonical digests are internally consistent. This proves
  record consistency, not the truth of the unavailable upstream snapshot.
- The candidate has 62 regular files, no symlinks or special files, and remained byte-for-byte
  unchanged during review.
- JSON parsing, shell syntax, the pack verifier, and a narrow independent credential-pattern screen
  completed as recorded in `VALIDATION.md`.
- The C probe compiled cleanly with strict warnings, ran successfully, and honored requested exit
  status 17. The static-link failure was reproduced exactly and is honestly documented.
- Requirements, concepts, design prompts, explicit non-goals, disposable-host warnings, and the
  standard-library-only module layout are useful to a systems learner.

## Recommendation

Fix the child-entry and CLI grammar defects, add a real Go CI evidence record, define generated-code
licensing, and obtain a harness-controlled learner-view/transfer check. The current artifact should
remain `GENERATED + PARTIAL`; it is neither tested nor transfer-verified nor productionized.
