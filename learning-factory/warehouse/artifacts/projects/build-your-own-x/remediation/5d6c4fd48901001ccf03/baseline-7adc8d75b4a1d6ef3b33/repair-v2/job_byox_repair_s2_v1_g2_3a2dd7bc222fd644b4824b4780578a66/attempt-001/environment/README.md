# Environment

The core exercise needs Python 3.11 and its standard library. Linux execution additionally needs
util-linux `unshare` with user, mount, UTS, IPC, PID, and network namespace options. Kernel policy
may deny unprivileged user namespaces even when the executable is installed.

The complete source artifact is instructor-only. Create disjoint distribution views only into a
path that does not already exist:

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
"$PYTHON311" environment/verify_pack.py
"$PYTHON311" environment/export_views.py create /path/to/new-export-directory
"$PYTHON311" environment/export_views.py verify /path/to/new-export-directory/learner --role learner
"$PYTHON311" environment/export_views.py verify /path/to/new-export-directory/instructor --role instructor
```

The learner export is an allowlist copy, not a request to ignore readable answer directories. Each
view's `environment/VIEW_MANIFEST.json` covers every payload file and every directory; verification
rejects missing, added, changed, symlink, or special entries. The creation summary prints the
manifest digest that a distributor must retain outside the view. The source artifact has no static
view manifest because the factory provides its own content-addressed inventory.

Run the nonmutating probe:

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
"$PYTHON311" -c 'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
"$PYTHON311" environment/check_host.py
```

The probe attempts only `unshare --user --map-root-user -- true`, with a five-second timeout and
captured output. Failure is expected on restricted builders and means integration stays `PARTIAL`.
It does not prove that chroot, proc mounting, UID mapping, or workload containment is correct.

`verify_pack.py` checks the complete canonical file set (including implementation and tests),
forbidden-path absence, file types, manifest shape, the separately declared exact-document digest
for `PROVENANCE.json`, generated view manifests when present, and obvious credential patterns. From
the repository root, `"$PYTHON311" environment/verify_pack.py` runs that packaging check; it is not
an independent solution validator. Override `PYTHON311` on hosts where Python 3.11 or newer is
installed elsewhere.
