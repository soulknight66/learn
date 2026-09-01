# Reproducible integration fixture

The fixture is a tiny statically linked C program rather than a downloaded image. Build it only on a
Linux machine whose C toolchain supports static linking:

```text
./make-rootfs.sh /absolute/path/to/new-rootfs
```

The script creates (but never deletes) the target's `bin/` and `proc/` directories and writes
`bin/probe`. It refuses `/`, relative paths, symbolic-link targets, and nonempty targets. Review the
script before running it with elevated privileges.

After completing the Go implementation, use a disposable VM:

```text
cd ../starter
go build -o tinycontainer ./cmd/tinycontainer
./tinycontainer run --rootfs /absolute/path/to/new-rootfs -- /bin/probe
```

Expected properties are `hostname=tinybox`, `pid=1`, and `proc=mounted`. The exact host policy may
deny user namespaces, mount namespaces, static linking, or proc mounts. Such a denial is an
environmental result to record, not a reason to weaken isolation.

The generator host compiled and ran the probe dynamically, confirming the C source, but lacked both
the static C runtime archive needed by this rootfs script and a Go toolchain. See `VALIDATION.md` for
the observed commands and do not treat the dynamic compile as a usable chroot fixture.
