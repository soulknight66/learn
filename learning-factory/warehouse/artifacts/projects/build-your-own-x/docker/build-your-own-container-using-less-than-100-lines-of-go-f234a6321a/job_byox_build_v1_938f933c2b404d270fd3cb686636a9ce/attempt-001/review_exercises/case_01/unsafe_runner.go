//go:build linux

package reviewcase

import (
	"os"
	"os/exec"
	"strings"
	"syscall"
)

// Launch is intentionally flawed code for review. Do not use it to run a command.
func Launch(rootfs, command string) error {
	if err := syscall.Chroot(rootfs); err != nil {
		return err
	}
	cmd := exec.Command("/bin/sh", "-c", strings.TrimSpace(command))
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Cloneflags: syscall.CLONE_NEWPID | syscall.CLONE_NEWUTS,
	}
	return cmd.Run()
}
