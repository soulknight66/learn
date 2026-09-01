//go:build linux

package tinycontainer

import (
	"fmt"
	"os"
	"os/exec"
	"syscall"
)

func currentHostIDs() (int, int) {
	return os.Getuid(), os.Getgid()
}

func configureCommand(cmd *exec.Cmd, plan LaunchPlan) error {
	attr := &syscall.SysProcAttr{
		Cloneflags: plan.CloneFlags,
		Pdeathsig:  syscall.SIGKILL,
	}
	for _, mapping := range plan.UIDMappings {
		attr.UidMappings = append(attr.UidMappings, syscall.SysProcIDMap{
			ContainerID: mapping.ContainerID,
			HostID:      mapping.HostID,
			Size:        mapping.Size,
		})
	}
	for _, mapping := range plan.GIDMappings {
		attr.GidMappings = append(attr.GidMappings, syscall.SysProcIDMap{
			ContainerID: mapping.ContainerID,
			HostID:      mapping.HostID,
			Size:        mapping.Size,
		})
	}
	if len(plan.GIDMappings) != 0 {
		attr.GidMappingsEnableSetgroups = !plan.DisableSetgroups
	}
	cmd.SysProcAttr = attr
	return nil
}

func enterAndExec(cfg Config) error {
	if err := ValidateConfig(cfg); err != nil {
		return fmt.Errorf("validate child configuration: %w", err)
	}
	if err := syscall.Mount("", "/", "", uintptr(syscall.MS_REC|syscall.MS_PRIVATE), ""); err != nil {
		return fmt.Errorf("make mount tree private: %w", err)
	}
	if err := syscall.Mount(cfg.RootFS, cfg.RootFS, "", uintptr(syscall.MS_BIND|syscall.MS_REC), ""); err != nil {
		return fmt.Errorf("bind rootfs onto itself: %w", err)
	}
	if err := syscall.Sethostname([]byte(cfg.Hostname)); err != nil {
		return fmt.Errorf("set hostname: %w", err)
	}
	if err := syscall.Chroot(cfg.RootFS); err != nil {
		return fmt.Errorf("change root: %w", err)
	}
	if err := syscall.Chdir("/"); err != nil {
		return fmt.Errorf("change working directory: %w", err)
	}
	if cfg.MountProc {
		if err := syscall.Mount("proc", "/proc", "proc", 0, ""); err != nil {
			return fmt.Errorf("mount proc: %w", err)
		}
	}
	environment := cfg.Environment
	if len(environment) == 0 {
		environment = []string{}
	}
	if err := syscall.Exec(cfg.Command[0], cfg.Command, environment); err != nil {
		return fmt.Errorf("exec contained command: %w", err)
	}
	return nil
}

func closeOnExec(fd int) {
	syscall.CloseOnExec(fd)
}

func platformExitCode(exit *exec.ExitError) int {
	if code := exit.ExitCode(); code >= 0 {
		return code
	}
	if status, ok := exit.Sys().(syscall.WaitStatus); ok && status.Signaled() {
		return 128 + int(status.Signal())
	}
	return 125
}
