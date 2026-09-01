# MiniCTR: build a small Linux container runtime in Bash

MiniCTR is a systems-programming challenge about the boundary between a process and a container.
You will finish a Bash command-line tool that registers a root filesystem, launches one command in
Linux namespaces, reports durable state, and cleans up after success, failure, and interruption.

The repository starts deliberately incomplete. The learner-facing starter contains the CLI shape and
validation scaffolding, but every state-changing operation and the namespace launcher still has a
`TODO`. Public tests describe observable behavior without providing an implementation. An untouched
starter is therefore expected to fail part of the suite.

This is an independently authored exercise. It does not copy the linked catalog project, and it is not
a production container engine.

## What you will learn

By completing the project you will practice:

- distinguishing a root filesystem from a complete container image;
- combining user, mount, PID, UTS, IPC, and network namespaces;
- reasoning about `chroot`, mount propagation, and a container-local `/proc`;
- passing command arguments as an argv vector instead of re-parsing a command string;
- keeping durable state separate from transient process state;
- making create/run/delete transitions safe under concurrency;
- propagating exit status and cleaning up after signals; and
- designing a privileged-looking program so most behavior can be tested without privileges.

## The command-line contract

Your executable is `starter/minictr` and has four operations:

```text
minictr create NAME ROOTFS
minictr run NAME COMMAND [ARG...]
minictr ps
minictr delete NAME
```

`create` registers an existing root filesystem; it does not download or copy one. `run` starts exactly
one command using that registration. `ps` prints registered instances in a stable tab-separated
format. `delete` removes an idle registration. State lives below `MINICTR_HOME`, which makes isolated
tests and disposable experiments possible.

Read [REQUIREMENTS.md](REQUIREMENTS.md) before deciding on an on-disk layout. The requirements define
observable behavior and safety properties, but intentionally leave the implementation to you.

## Suggested progression

Work in small, testable slices:

1. Run the environment check and read the threat model.
2. Implement `create`, `ps`, and `delete` without invoking any namespace tools.
3. Implement `run` against the fake isolator used by the public tests. Preserve arguments, output, and
   exit status exactly.
4. Add an exclusive-run guard and reliable cleanup. Test concurrent `run`/`delete` behavior with the
   fake isolator.
5. Implement `starter/lib/isolate.sh` with Linux namespace and root-filesystem isolation.
6. In a disposable environment, perform an explicit real-isolation smoke test with a root filesystem
   you supply.

The order matters pedagogically: deterministic control-plane behavior can be made correct before you
debug host kernel policy.

## Start here

All routine commands are safe to run without root:

```bash
./environment/check.sh
bash -n starter/minictr starter/lib/runtime.sh starter/lib/isolate.sh
bash public_tests/test_minictr.sh
```

You can test a different executable without moving files:

```bash
MINICTR_BIN=/absolute/path/to/minictr bash public_tests/test_minictr.sh
```

The public suite creates a fresh temporary state directory and a fake root filesystem for each case.
It never asks the host to create namespaces or mounts. See [public_tests/README.md](public_tests/README.md)
for its scope and limitations.

## Real isolation is an explicit second test layer

The actual isolator is Linux-specific. Even when `unshare`, `mount`, and `chroot` are installed, a host
may disable unprivileged user namespaces or deny required operations through a container policy,
security module, or seccomp filter. Tool presence is not evidence that isolation will work.

This repository does not fetch or construct a root filesystem. Supply a disposable, trusted rootfs
that contains the requested command and all of its runtime dependencies. Do not point MiniCTR at `/`,
a production filesystem, or irreplaceable data. Never run an unfinished isolator with elevated
privileges on a machine you care about.

## Repository guide

- `starter/` — the only implementation area learners normally edit;
- `public_tests/` — deterministic, privilege-free contract tests;
- `environment/` — host capability notes and a non-invasive checker;
- `CONCEPTS.md` — conceptual background, not an implementation recipe;
- `DESIGN_QUESTIONS.md` — questions to answer in your own design notes;
- `REQUIREMENTS.md` — the normative observable contract; and
- `sealed/` — evaluator-owned material, outside the learner task.

## Completion criteria

A completed learner implementation should:

- pass every public test without changing the tests;
- leave no `TODO` paths reachable by a valid operation;
- use no `eval`, shell command strings, or sourced state files;
- behave deterministically for duplicate, missing, stale, and active instances;
- leave an instance usable after a child exits nonzero or is interrupted; and
- demonstrate, separately and honestly, whether real namespace isolation is supported by the host.

Passing the public suite proves only the documented control-plane contract. It does not establish that
the runtime is secure against hostile root filesystems, equivalent to an OCI runtime, or ready for
production.
