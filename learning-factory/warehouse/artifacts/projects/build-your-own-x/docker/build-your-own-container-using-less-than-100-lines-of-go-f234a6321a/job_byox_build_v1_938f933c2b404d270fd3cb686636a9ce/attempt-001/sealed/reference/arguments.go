package tinycontainer

import (
	"flag"
	"fmt"
	"io"
	"strconv"
)

type stringList []string

func (s *stringList) String() string { return fmt.Sprint([]string(*s)) }
func (s *stringList) Set(value string) error {
	*s = append(*s, value)
	return nil
}

// ParseRunArgs parses and validates the public CLI invocation.
func ParseRunArgs(args []string) (Config, error) {
	if len(args) == 0 || args[0] != "run" {
		return Config{}, fmt.Errorf("expected run subcommand")
	}
	cfg, _, err := parseConfigArgs(args[1:], false)
	return cfg, err
}

// EncodeChildArgs creates argv for the internal re-execution phase.
func EncodeChildArgs(cfg Config) []string {
	args := []string{
		childMarker,
		"--error-fd=" + strconv.Itoa(childErrorFD),
		"--rootfs", cfg.RootFS,
		"--hostname", cfg.Hostname,
		"--mount-proc=" + strconv.FormatBool(cfg.MountProc),
		"--userns=" + strconv.FormatBool(cfg.UseUserNamespace),
	}
	if len(cfg.Environment) == 0 {
		args = append(args, "--empty-env=true")
	} else {
		for _, entry := range cfg.Environment {
			args = append(args, "--env", entry)
		}
	}
	args = append(args, "--")
	return append(args, cfg.Command...)
}

// ParseChildArgs parses and validates an internal re-execution invocation.
func ParseChildArgs(args []string) (Config, error) {
	cfg, _, err := parseChildConfig(args)
	return cfg, err
}

func parseChildConfig(args []string) (Config, int, error) {
	if !IsChildInvocation(args) {
		return Config{}, -1, fmt.Errorf("expected internal child marker")
	}
	return parseConfigArgs(args[1:], true)
}

func parseConfigArgs(args []string, internal bool) (Config, int, error) {
	cfg := DefaultConfig()
	var environment stringList
	var emptyEnvironment bool
	errorFD := -1

	fs := flag.NewFlagSet("tinycontainer", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	fs.StringVar(&cfg.RootFS, "rootfs", "", "absolute root filesystem path")
	fs.StringVar(&cfg.Hostname, "hostname", cfg.Hostname, "contained hostname")
	fs.BoolVar(&cfg.MountProc, "mount-proc", cfg.MountProc, "mount a new proc filesystem")
	fs.BoolVar(&cfg.UseUserNamespace, "userns", cfg.UseUserNamespace, "create a user namespace")
	fs.Var(&environment, "env", "contained environment entry")
	if internal {
		fs.BoolVar(&emptyEnvironment, "empty-env", false, "use an empty environment")
		fs.IntVar(&errorFD, "error-fd", -1, "internal setup error descriptor")
	}
	if err := fs.Parse(args); err != nil {
		return Config{}, -1, fmt.Errorf("parse arguments: %w", err)
	}
	if emptyEnvironment && len(environment) != 0 {
		return Config{}, -1, fmt.Errorf("parse arguments: empty-env conflicts with env")
	}
	if emptyEnvironment {
		cfg.Environment = nil
	} else if len(environment) != 0 {
		cfg.Environment = append([]string(nil), environment...)
	}
	cfg.Command = append([]string(nil), fs.Args()...)
	if internal && errorFD != childErrorFD {
		return Config{}, -1, fmt.Errorf("parse arguments: invalid child error descriptor")
	}
	if err := ValidateConfig(cfg); err != nil {
		return Config{}, errorFD, err
	}
	return cfg, errorFD, nil
}

func encodedChildErrorFD(args []string) int {
	want := "--error-fd=" + strconv.Itoa(childErrorFD)
	for _, arg := range args {
		if arg == want {
			return childErrorFD
		}
	}
	return -1
}
