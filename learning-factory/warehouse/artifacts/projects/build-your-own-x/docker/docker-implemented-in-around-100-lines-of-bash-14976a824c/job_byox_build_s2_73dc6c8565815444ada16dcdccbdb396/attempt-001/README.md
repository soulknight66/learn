# Tinybox: build a container runtime in Bash

Tinybox is a from-scratch learning challenge about the small amount of orchestration around Linux
container primitives. You will implement a Bash CLI that creates private root filesystem copies,
tracks container lifecycle state, preserves command arguments, and delegates isolation to a Linux
namespace runner.

This is an independent exercise inspired only by the catalog topic “Docker implemented in around
100 lines of bash.” The linked project is provenance, not source material. No linked code or prose is
included here.

## What you build

Implement `starter/tinybox.sh` and `starter/runner.sh` according to `REQUIREMENTS.md`. The finished
CLI supports:

```text
tinybox.sh create NAME ROOTFS
tinybox.sh run NAME -- /absolute/program [ARG ...]
tinybox.sh list
tinybox.sh inspect NAME
tinybox.sh delete NAME
```

The controller is testable without privileges because `TINYBOX_RUNNER` can select a deterministic
test double. The real runner is Linux-specific and may be blocked by user-namespace policy even when
`unshare` is installed.

## Suggested progression

1. Make `help`, argument checking, and name validation deterministic.
2. Implement an isolated state directory and copy-on-create root filesystems.
3. Add atomic status files and enforce the lifecycle in `REQUIREMENTS.md`.
4. Add per-container exclusion so racing mutations cannot both succeed.
5. Preserve the command as an argv array when invoking the runner.
6. Implement the Linux namespace runner and investigate which kernel features the host permits.

Run the public contract tests from the repository root:

```bash
bash public_tests/test_contract.sh starter/tinybox.sh
bash environment/check.sh
```

The starter is intentionally incomplete, so the contract suite initially reports failures. Do not
use Tinybox to run untrusted workloads. It is an educational runtime, not a security boundary or a
production container engine.

## Reading map

- `REQUIREMENTS.md` is the normative behavioral contract.
- `CONCEPTS.md` explains the kernel and filesystem ideas.
- `DESIGN_QUESTIONS.md` supplies checkpoints before each stage.
- `starter/README.md` maps TODOs to testable milestones.
- `environment/README.md` documents dependencies and privilege limits.
- `public_tests/README.md` explains the visible tests without revealing a solution.

Independent validation is required. The repository status remains `GENERATED` + `PARTIAL` even when
the deterministic reference tests pass, because the real namespace backend could not be certified
as portable or production-safe here.
