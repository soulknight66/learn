# Case 1 sealed review

1. **Critical — mutates the reviewer process root.** `syscall.Chroot` runs before a child exists, so
   the calling process changes its own filesystem view permanently. Create a re-executed child and
   perform all irreversible setup only there.
2. **Critical — shell injection.** A caller-controlled string is interpreted by `/bin/sh -c`.
   Accept an argv slice and execute its absolute first element directly.
3. **High — no mount namespace or propagation control.** Filesystem mounts are not isolated, and
   there is no private propagation step. Create a new mount namespace before touching mounts.
4. **High — rootfs validation absent.** `/`, relative paths, symlinks, files, and mutable paths are
   accepted. Apply the documented validation and still acknowledge its pathname races.
5. **High — no user namespace or privilege model.** The function either fails for an ordinary user
   or operates with host capabilities. Define identity mappings and capability policy explicitly.
6. **Medium — hostname never set.** A UTS namespace is created but has no requested identity.
7. **Medium — wrong setup order.** Namespace flags apply only when `cmd` starts, which happens after
   the parent has already changed root.
8. **Medium — no proc filesystem.** PID tools in the rootfs would observe an absent or incorrect
   proc view.
9. **Medium — unbounded lifecycle.** There is no context cancellation, parent-death signal, setup
   diagnostic channel, or signal-status normalization.
10. **Low — whitespace mutation.** `TrimSpace` silently changes the command, an unexpected semantic
    transformation even before the shell interprets it.

The safe repair is architectural rather than a local patch: validate and plan in the parent, clone
the required namespaces during re-exec, make mounts private, enter the root, and exec an argv vector.
