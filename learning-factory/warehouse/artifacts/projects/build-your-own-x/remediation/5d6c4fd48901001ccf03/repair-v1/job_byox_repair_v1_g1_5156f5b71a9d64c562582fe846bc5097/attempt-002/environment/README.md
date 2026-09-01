# Environment diagnostics

The deterministic Minibox stages need only Python's standard library. The
optional real backend has a narrower platform envelope: Linux, util-linux
`unshare`, the expected namespace interfaces, and a host policy that permits an
unprivileged user namespace.

Run the read-only report from the repository root:

```bash
python3 environment/probe.py
```

The script prints JSON describing:

- the operating system and Python version;
- whether the process appears to be running as root;
- the discovered `unshare` and `true` executable paths;
- visible `/proc/self/ns` entries and their host-side namespace identities; and
- readable user-namespace-related kernel settings.

Static indicators are inconclusive. To ask the installed `unshare` program to
create one short-lived user namespace, opt in explicitly:

```bash
python3 environment/probe.py --try-userns
```

The active probe runs an argument vector equivalent in intent to `unshare`
with user mapping followed by `true`. It uses captured output, a bounded
timeout, and a separate process group. It does not mount a rootfs, start a
Minibox payload, use a shell, request network access, or make persistent
changes. Host auditing and security policy may still observe or deny it.

The diagnostic exits successfully after producing a report even when a feature
is missing or denied. Inspect `user_namespace_test.status` and its bounded
stderr field; this command reports capability rather than grading the learner
implementation.

Common outcomes include:

- `not_requested`: only static checks were requested;
- `not_linux`: the optional backend cannot run on this host;
- `command_missing`: `unshare` or the no-op payload was not found;
- `success`: this narrow user-namespace operation worked at probe time;
- `failed`: the kernel or host policy rejected it; and
- `timeout`: the probe was terminated after its deadline.

Even `success` is not proof that mount, PID, UTS, IPC, or network namespaces
will work, that child setup is correct, or that a workload is securely
contained. Conversely, a denied active probe does not invalidate configuration,
resolution, planning, state, or fake-backend tests.

Never respond to a failed probe by running the challenge as root. Use a
disposable Linux VM or an explicitly configured development environment for
optional integration work.

`live_payload.c` is a benign payload for a later, explicit end-to-end smoke
test. If the host C toolchain can build it, first save the probe report, then compile it into
`/bin/live-payload` inside a temporary rootfs that also has an empty `/proc`
directory. Do not commit the binary or rootfs. It reports its PID, hostname,
PID and mount namespace symlink identities, whether `/proc` is actually a
procfs mount according to mountinfo, and the bounded sorted list and count of
numeric PID directories visible there. It exits with status 17 only when it is
PID 1, sees hostname `minibox`, sees a procfs mount with PID 1, and can read both
namespace identities; a failed assertion exits 70. This also verifies that a
genuine nonzero payload result remains distinct from namespace setup failure.

For isolation evidence, compare `pid_namespace` and `mount_namespace` from the
payload with `proc_namespace_ids.pid` and `proc_namespace_ids.mount` in the
host-side probe report; both must differ. Inspect `proc_pids` for unexpected
host processes and retain the mount metadata. Merely reading
`/proc/self/status`, seeing PID 1, or seeing different namespace identifiers in
isolation is not a complete containment test. Run this only in a disposable
integration environment and preserve the exact observations.
