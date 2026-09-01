# Environment and safety

MiniCTR has two deliberately separate execution environments: a privilege-free public-test layer and a
Linux namespace integration layer. Do not infer success in the second from success in the first.

## Public-test prerequisites

The deterministic suite needs:

- Linux or another host capable of running Bash tests;
- Bash 4 or newer;
- `env`, `mktemp`, `sort`, and GNU-compatible `timeout`; and
- ordinary permission to create temporary files below `${TMPDIR:-/tmp}`.

No Bats or ShellCheck installation is required. The repository includes its own test runner and fake
isolator.

Run the non-invasive inventory:

```bash
./environment/check.sh
```

It only checks command availability and the kernel name. It does not create state, enter a namespace,
mount anything, change root, contact the network, or elevate privileges.

## Real-isolation prerequisites

The default isolator additionally targets Linux tools commonly named:

- `unshare` for namespace and user-ID mapping setup;
- `mount` for private propagation and a container-local proc filesystem; and
- `chroot` for changing the apparent filesystem root.

Check only that those executables exist with:

```bash
./environment/check.sh --require-isolation-tools
```

Even a zero result does not establish that the calls are permitted. User namespaces may be disabled,
namespace quotas may be exhausted, or an outer container/seccomp/LSM policy may reject setup. A correct
MiniCTR reports that run as unsupported and does not execute the requested command without isolation.

## Root filesystem policy

This challenge intentionally does not download, unpack, or manufacture a root filesystem. A real smoke
test requires a disposable absolute directory supplied by the learner. It must contain the selected
command and, for a dynamically linked program, its loader and shared libraries at the paths expected by
that binary.

A rootfs made from host binaries is tied to that host’s architecture and ABI and should not be described
as portable. A shell script also needs its interpreter inside the rootfs. The public tests avoid these
variables by using an empty directory and replacing only the isolation helper.

Never use any of these as an experimental rootfs:

- `/`;
- a mounted production or user-data filesystem;
- a directory whose contents are not disposable; or
- a tree controlled by an untrusted party on a machine with valuable data.

MiniCTR must not modify or delete the rootfs during create/delete lifecycle operations.
Choose a state directory in a disjoint tree: neither `MINICTR_HOME` nor the rootfs may contain the
other. A correct implementation rejects overlap before creating state.

## Suggested integration-test containment

If your host permits namespace creation, perform real-isolation checks in a disposable virtual machine
or nested development container with no secrets and no important writable mounts. Start with a rootfs
whose contents you understand. Inspect namespace identities and mount state from both sides, test a
nonzero command, and verify no process or mount remains after exit.

Do not add `sudo` merely because an unprivileged test failed. Root execution changes the threat model and
can turn a cleanup bug into host damage. Diagnose the denied operation first.

## Optional developer tools

`shellcheck` is useful for finding unquoted expansions and array mistakes if available, but it is not a
substitute for adversarial argv tests. `findmnt` and `nsenter` can help inspect an integration run.
`busybox` can be useful when constructing your own disposable rootfs, but it is not provided or required
by this exercise.
