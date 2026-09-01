package tinycontainer

import (
	"fmt"
	"path/filepath"
)

// NamespaceFlags returns the required clone mask for this configuration.
func NamespaceFlags(useUserNamespace bool) (uintptr, error) {
	return platformNamespaceFlags(useUserNamespace)
}

// BuildLaunchPlan validates inputs without starting a process or changing namespaces.
func BuildLaunchPlan(cfg Config, selfPath string, hostUID, hostGID int) (LaunchPlan, error) {
	if err := ValidateConfig(cfg); err != nil {
		return LaunchPlan{}, fmt.Errorf("plan: %w", err)
	}
	if selfPath == "" || !filepath.IsAbs(selfPath) || filepath.Clean(selfPath) != selfPath {
		return LaunchPlan{}, fmt.Errorf("plan: executable path must be absolute and clean")
	}
	if hostUID < 0 || hostGID < 0 {
		return LaunchPlan{}, fmt.Errorf("plan: host UID and GID must not be negative")
	}
	flags, err := NamespaceFlags(cfg.UseUserNamespace)
	if err != nil {
		return LaunchPlan{}, fmt.Errorf("plan: %w", err)
	}
	plan := LaunchPlan{
		Executable: selfPath,
		Arguments:  EncodeChildArgs(cfg),
		CloneFlags: flags,
	}
	if cfg.UseUserNamespace {
		plan.UIDMappings = []IDMap{{ContainerID: 0, HostID: hostUID, Size: 1}}
		plan.GIDMappings = []IDMap{{ContainerID: 0, HostID: hostGID, Size: 1}}
		plan.DisableSetgroups = true
	}
	return plan, nil
}
