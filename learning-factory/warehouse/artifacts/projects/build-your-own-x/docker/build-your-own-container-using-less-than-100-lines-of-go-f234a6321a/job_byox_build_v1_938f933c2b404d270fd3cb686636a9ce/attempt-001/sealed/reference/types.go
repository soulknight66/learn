package tinycontainer

import (
	"errors"
	"fmt"
	"io"
)

const (
	childMarker          = "__tinycontainer_init"
	childErrorFD         = 3
	maxChildSetupMessage = 8192
)

var ErrNotLinux = errors.New("tinycontainer: Linux is required")

// Config describes one contained process.
type Config struct {
	RootFS           string
	Hostname         string
	Command          []string
	Environment      []string
	MountProc        bool
	UseUserNamespace bool
}

// IDMap describes one contiguous user-namespace identity mapping.
type IDMap struct {
	ContainerID int
	HostID      int
	Size        int
}

// LaunchPlan is the deterministic boundary between validation and process creation.
type LaunchPlan struct {
	Executable       string
	Arguments        []string
	CloneFlags       uintptr
	UIDMappings      []IDMap
	GIDMappings      []IDMap
	DisableSetgroups bool
}

// IO carries the streams connected to the contained process.
type IO struct {
	Stdin  io.Reader
	Stdout io.Writer
	Stderr io.Writer
}

// ExitError reports the contained command's exit status.
type ExitError struct {
	Code int
}

func (e *ExitError) Error() string {
	return fmt.Sprintf("contained process exited with status %d", e.Code)
}

// DefaultEnvironment returns a fresh copy of the exercise's deterministic environment.
func DefaultEnvironment() []string {
	return []string{
		"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
		"HOME=/",
		"TERM=xterm",
	}
}

// DefaultConfig returns the defaults used by both public and internal parsing.
func DefaultConfig() Config {
	return Config{
		Hostname:         "tinybox",
		Environment:      DefaultEnvironment(),
		MountProc:        true,
		UseUserNamespace: true,
	}
}

// IsChildInvocation recognizes only the reserved first argument.
func IsChildInvocation(args []string) bool {
	return len(args) > 0 && args[0] == childMarker
}
