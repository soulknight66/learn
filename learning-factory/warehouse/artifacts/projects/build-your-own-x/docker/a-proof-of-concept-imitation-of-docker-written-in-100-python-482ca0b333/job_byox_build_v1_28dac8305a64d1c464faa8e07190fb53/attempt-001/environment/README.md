# Environment

The deterministic implementation and tests need Python 3.11 or newer and no third-party packages.

Real isolation additionally depends on Linux, util-linux `unshare`, host user-namespace policy, and a rootfs containing the payload and its loader/libraries. Check only the first three conditions with:

```bash
python3 environment/probe_namespaces.py
```

The probe runs `unshare --user --map-root-user -- true` with a five-second timeout. It prints JSON and returns nonzero if unavailable or denied. A failed probe does not invalidate pure-unit behavior and must not be rewritten as a passing result.
