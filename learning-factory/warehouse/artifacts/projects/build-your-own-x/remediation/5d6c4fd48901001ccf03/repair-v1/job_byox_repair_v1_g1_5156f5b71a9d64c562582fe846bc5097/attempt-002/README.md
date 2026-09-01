# Minibox

Minibox is a staged exercise in building a small, educational Linux container
runtime in Python. It is deliberately much narrower than Docker, Podman, or an
OCI runtime. The goal is to practice trustworthy input handling, filesystem
confinement, namespace planning, durable state transitions, and testable
process execution without pretending that a few namespace flags constitute a
production sandbox.

The exercise requires Python 3.10 or newer and otherwise uses only the standard
library for its deterministic stages.

You will implement the `minibox` package under `starter/`. The deterministic
parts of the exercise run anywhere Python's standard library runs. The final,
optional integration stage needs Linux, a compatible `unshare` utility, and a
host policy that permits unprivileged user namespaces.

## Learning path

1. **Strict configuration** — turn an untrusted JSON object into a validated
   `ContainerSpec` with a closed schema and explicit defaults.
2. **Rootfs-safe lookup** — resolve a guest command beneath a chosen root
   filesystem without following symlinks or accepting traversal.
3. **Isolation planning** — produce a deterministic `unshare` argument vector
   and a precise list of requested namespaces. Planning does not execute it.
4. **Atomic lifecycle state** — persist `CREATED`, `RUNNING`, `EXITED`, and
   `FAILED` transitions while enforcing compare-and-transition semantics.
5. **Injectable execution** — coordinate state with a backend through a small
   interface that can be replaced by a fake in unit tests.
6. **Optional Linux backend** — on a suitable disposable Linux environment,
   explore executing the plan with `unshare` and a child bootstrap module.

If an instructor reveals the gated follow-ons, continue in this order:
`adversarial/README.md`, `debugging/README.md`,
`review_exercises/README.md`, then `benchmarks/README.md`. These are optional
enrichment rather than core submissions; they are deliberately absent from the
initial learner archive.

The normative behavior is in [REQUIREMENTS.md](REQUIREMENTS.md). Read
[CONCEPTS.md](CONCEPTS.md) for background, then record your own reasoning using
[DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md).

## Start here

Run commands from the repository root:

```bash
python3 -c 'import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
python3 environment/probe.py
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

The preflight must exit 0; if it does not, select a Python 3.10-or-newer
interpreter explicitly for every later command. Then work only under
`starter/`, rerunning the public tests after small changes. The tests use the
standard-library `unittest` framework. No Docker daemon and no elevated
privileges are required for the deterministic stages.

For shorter feedback, run one stage at a time (later stages assume earlier
ones already work):

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_config.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_rootfs.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_plan.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_state.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_runtime.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_api.py' -v
```

The required learner-facing module surface is:

- `minibox.config`: `ContainerSpec`, `from_dict`, and `load_spec`
- `minibox.rootfs`: `resolve_executable`
- `minibox.plan`: `IsolationPlan` and `build_plan`
- `minibox.state`: `ContainerState` and `StateStore`, including uncertain-commit recovery
- `minibox.runtime`: `Runtime`, `ExecutionResult`, and
  `LinuxSubprocessBackend`

The package root re-exports these values and the supporting exception
hierarchy. The full behavioral contract is listed in the requirements.

## What Minibox does not promise

Minibox is not a security boundary for hostile code. In particular, the core
exercise does not provide a complete mount setup, `pivot_root`, capability
management, seccomp, cgroups, image verification, resource accounting, or an
OCI-compatible lifecycle. A namespace *plan* is only data. Even successful
`unshare` execution may still leave access to host resources unless the child
bootstrap establishes every necessary boundary correctly.

Do not run untrusted programs with Minibox. Do not run it as root. Use only
small, purpose-built root filesystems and benign commands in a disposable
environment. `network_mode="host"` explicitly requests no network namespace
and therefore shares the caller's network view.

Linux distributions, CI sandboxes, containers, WSL versions, and enterprise
security policies frequently disable unprivileged user namespaces. The mere
presence of `/usr/bin/unshare` does not prove that the optional backend can
run. A denied user-namespace probe is an expected environment limitation, not
evidence that the deterministic implementation is wrong.

Stages 1 through 5 are the required deterministic core. Stage 6, the real
Linux backend, is optional. The full production pack also contains gated
adversarial-testing, debugging, code-review, and benchmarking exercises; an
instructor may reveal those separately, but they are not core submissions and
are not part of the initial learner archive.

## Repository boundary

Learners must receive only the machine-generated learner archive, containing
the six top-level learner documents plus `starter/`, `public_tests/`, and
`environment/`. A complete production pack that still contains `sealed/` is
not a learner workspace and must not be distributed as one. Material under
`sealed/` belongs to the independent evaluation boundary; do not inspect or
modify it while solving the challenge. See [AGENTS.md](AGENTS.md) for the
workspace rules.

The independently generated Minibox material is available under the MIT
License. The linked tutorial is not included and its license remains
`NOASSERTION`; the grant does not apply to it.
