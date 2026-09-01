//go:build !linux

package tinycontainer

import "os/exec"

func currentHostIDs() (int, int) { return 0, 0 }

func configureCommand(*exec.Cmd, LaunchPlan) error { return ErrNotLinux }

func enterAndExec(Config) error { return ErrNotLinux }

func closeOnExec(int) {}

func platformExitCode(exit *exec.ExitError) int {
	if code := exit.ExitCode(); code >= 0 {
		return code
	}
	return 125
}
