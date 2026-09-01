# Exercise 1 answer

`make-private:/` must be first: a newly cloned mount namespace can retain shared propagation
relationships, so bind or proc mounts performed earlier may propagate outside the intended boundary.

`mount-proc:/proc` must occur after `chroot` and `chdir`. Before changing root, `/proc` names the
host-visible path and could target the wrong mountpoint. The corrected sequence is exactly the test's
expected value: private propagation, self-bind rootfs, hostname, chroot, chdir, fresh proc, exec.
