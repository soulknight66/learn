package mountorder

// Steps returns a proposed order for filesystem setup. The sequence contains one design bug.
func Steps(rootfs string, mountProc bool) []string {
	steps := []string{"bind:" + rootfs}
	if mountProc {
		steps = append(steps, "mount-proc:/proc")
	}
	steps = append(steps,
		"make-private:/",
		"set-hostname",
		"chroot:"+rootfs,
		"chdir:/",
		"exec",
	)
	return steps
}
