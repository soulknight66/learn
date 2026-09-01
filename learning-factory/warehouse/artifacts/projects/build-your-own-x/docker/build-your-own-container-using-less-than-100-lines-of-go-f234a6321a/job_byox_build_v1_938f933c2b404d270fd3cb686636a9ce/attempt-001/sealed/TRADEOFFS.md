# Tradeoffs and alternatives considered

## Chroot versus pivot_root

The reference uses `chroot` after making a private mount namespace and bind-mounting the rootfs. That
keeps the exercise compact and makes failures easy to attribute. `pivot_root` more completely
disconnects the old root but requires a root mountpoint, an old-root staging directory, detach
unmounting, cleanup, and more error states. Neither design is sufficient while broad capabilities and
host-controlled file descriptors remain available.

## Workload as PID 1 versus retained init

Executing the workload directly yields transparent exit status and minimal code. It also delegates
signal handling and orphan reaping to software that may not expect PID 1 semantics. A retained init
would forward signals, reap descendants, and translate status, but needs careful race handling and
tests around process groups and cancellation.

## User namespace by default

The public CLI defaults to one host UID/GID mapped to container root. This can avoid requiring global
root and narrows capabilities, but many managed kernels disable unprivileged user namespaces or
restrict mounts inside them. Disabling the flag is explicit and then requires suitable host
capabilities; it is not an isolation improvement.

## Fixed argv encoding versus JSON

Repeated flags make every field visible and avoid a decoder dependency or shell parsing. JSON would
be easier to extend but needs careful size limits and still exposes its contents in the process list.
A production supervisor would send a length-bounded configuration over a protected descriptor.

## Error pipe versus reserved exit code alone

A reserved status cannot distinguish setup failure from a workload choosing that status. The
close-on-exec pipe has a crisp success signal—EOF at exec—and permits a bounded diagnostic. It adds
descriptor lifecycle complexity and still needs an authenticated parent-child relationship, which
the direct fork/re-exec provides here.

## Standard library syscall versus external syscall package

`syscall` avoids downloads on an offline learning host and exposes the core operations directly. It
is frozen and less ergonomic than `golang.org/x/sys/unix`. A maintained runtime should pin and vendor
the latter or wrap raw operations behind a deliberately reviewed platform layer.
