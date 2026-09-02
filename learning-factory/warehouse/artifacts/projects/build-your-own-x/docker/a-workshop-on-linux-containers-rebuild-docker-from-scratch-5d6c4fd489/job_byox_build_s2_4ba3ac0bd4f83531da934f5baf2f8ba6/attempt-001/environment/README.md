# Environment

The core exercise needs Python 3.11 and its standard library. Linux execution additionally needs
util-linux `unshare` with user, mount, UTS, IPC, PID, and network namespace options. Kernel policy
may deny unprivileged user namespaces even when the executable is installed.

Run the nonmutating probe:

```bash
python3 environment/check_host.py
```

The probe attempts only `unshare --user --map-root-user -- true`, with a five-second timeout and
captured output. Failure is expected on restricted builders and means integration stays `PARTIAL`.
It does not prove that chroot, proc mounting, UID mapping, or workload containment is correct.

`verify_pack.py` checks the required paths, forbidden-path absence, file types, manifest shape, and
obvious credential patterns. It is a packaging check, not an independent solution validator.
