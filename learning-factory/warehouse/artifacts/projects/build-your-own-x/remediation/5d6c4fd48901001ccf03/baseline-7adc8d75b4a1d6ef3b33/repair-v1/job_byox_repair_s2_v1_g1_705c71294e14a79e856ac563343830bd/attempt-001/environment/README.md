# Environment

The core exercise needs Python 3.11 and its standard library. Linux execution additionally needs
util-linux `unshare` with user, mount, UTS, IPC, PID, and network namespace options. Kernel policy
may deny unprivileged user namespaces even when the executable is installed.

Run the nonmutating probe:

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
"$PYTHON311" -c 'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
"$PYTHON311" environment/check_host.py
```

The probe attempts only `unshare --user --map-root-user -- true`, with a five-second timeout and
captured output. Failure is expected on restricted builders and means integration stays `PARTIAL`.
It does not prove that chroot, proc mounting, UID mapping, or workload containment is correct.

`verify_pack.py` checks the required paths, forbidden-path absence, file types, manifest shape,
the separately declared exact-document digest for `PROVENANCE.json`, and obvious credential
patterns. From the repository root, `"$PYTHON311" environment/verify_pack.py` runs that packaging
check; it is not an independent solution validator. Override `PYTHON311` on hosts where Python
3.11 or newer is installed elsewhere.
