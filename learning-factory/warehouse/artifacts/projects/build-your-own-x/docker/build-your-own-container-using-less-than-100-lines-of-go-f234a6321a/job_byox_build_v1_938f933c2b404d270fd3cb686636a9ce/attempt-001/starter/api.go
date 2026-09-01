package tinycontainer

import "context"

// ValidateConfig checks every precondition that can be checked before namespace creation.
func ValidateConfig(cfg Config) error {
	// TODO: implement requirements R2-R6.
	return ErrNotImplemented
}

// ParseRunArgs parses and validates the public CLI invocation.
func ParseRunArgs(args []string) (Config, error) {
	// TODO: implement requirement R7 without invoking a shell.
	return Config{}, ErrNotImplemented
}

// EncodeChildArgs creates argv for the internal re-execution phase.
func EncodeChildArgs(cfg Config) []string {
	// TODO: implement the encoding half of requirement R8.
	return nil
}

// ParseChildArgs parses and validates an internal re-execution invocation.
func ParseChildArgs(args []string) (Config, error) {
	// TODO: implement the decoding half of requirement R8.
	return Config{}, ErrNotImplemented
}

// NamespaceFlags returns the required clone mask for this configuration.
func NamespaceFlags(useUserNamespace bool) (uintptr, error) {
	// TODO: return ErrNotLinux outside Linux and implement R10 on Linux.
	return 0, ErrNotImplemented
}

// BuildLaunchPlan validates inputs without starting a process or changing namespaces.
func BuildLaunchPlan(cfg Config, selfPath string, hostUID, hostGID int) (LaunchPlan, error) {
	// TODO: implement requirements R9-R12.
	return LaunchPlan{}, ErrNotImplemented
}

// Run launches the current executable in the namespaces described by cfg.
func Run(ctx context.Context, cfg Config, streams IO) error {
	// TODO: implement requirements R13-R14, with a Linux and non-Linux split.
	return ErrNotImplemented
}

// RunChildInvocation validates, configures, and execs an internal child invocation.
func RunChildInvocation(args []string) error {
	// TODO: implement requirements R15-R17. Never continue after a failed setup call.
	return ErrNotImplemented
}
