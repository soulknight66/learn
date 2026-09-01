package tinycontainer

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// ValidateConfig checks every precondition available before namespace creation.
func ValidateConfig(cfg Config) error {
	if cfg.RootFS == "" {
		return fmt.Errorf("rootfs: path is required")
	}
	if !filepath.IsAbs(cfg.RootFS) {
		return fmt.Errorf("rootfs: path must be absolute")
	}
	if filepath.Clean(cfg.RootFS) != cfg.RootFS {
		return fmt.Errorf("rootfs: path must already be clean")
	}
	if cfg.RootFS == string(filepath.Separator) {
		return fmt.Errorf("rootfs: host root is forbidden")
	}

	rootInfo, err := os.Lstat(cfg.RootFS)
	if err != nil {
		return fmt.Errorf("rootfs: inspect path: %w", err)
	}
	if rootInfo.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("rootfs: symbolic-link root is forbidden")
	}
	if !rootInfo.IsDir() {
		return fmt.Errorf("rootfs: path is not a directory")
	}

	if cfg.MountProc {
		procPath := filepath.Join(cfg.RootFS, "proc")
		procInfo, err := os.Lstat(procPath)
		if err != nil {
			return fmt.Errorf("rootfs: inspect proc mountpoint: %w", err)
		}
		if procInfo.Mode()&os.ModeSymlink != 0 || !procInfo.IsDir() {
			return fmt.Errorf("rootfs: proc mountpoint must be a real directory")
		}
	}

	if err := validateHostname(cfg.Hostname); err != nil {
		return err
	}
	if len(cfg.Command) == 0 {
		return fmt.Errorf("command: at least one argument is required")
	}
	if !filepath.IsAbs(cfg.Command[0]) {
		return fmt.Errorf("command: executable path must be absolute")
	}
	if filepath.Clean(cfg.Command[0]) != cfg.Command[0] {
		return fmt.Errorf("command: executable path must already be clean")
	}
	for _, arg := range cfg.Command {
		if strings.IndexByte(arg, 0) >= 0 {
			return fmt.Errorf("command: arguments must not contain NUL")
		}
	}
	if err := validateEnvironment(cfg.Environment); err != nil {
		return err
	}
	return nil
}

func validateHostname(hostname string) error {
	if len(hostname) == 0 || len(hostname) > 63 {
		return fmt.Errorf("hostname: length must be between 1 and 63 bytes")
	}
	for _, label := range strings.Split(hostname, ".") {
		if len(label) == 0 {
			return fmt.Errorf("hostname: labels must not be empty")
		}
		if label[0] == '-' || label[len(label)-1] == '-' {
			return fmt.Errorf("hostname: labels must not begin or end with a hyphen")
		}
		for i := 0; i < len(label); i++ {
			c := label[i]
			if !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
				(c >= '0' && c <= '9') || c == '-') {
				return fmt.Errorf("hostname: labels contain an invalid byte")
			}
		}
	}
	return nil
}

func validateEnvironment(environment []string) error {
	seen := make(map[string]struct{}, len(environment))
	for _, entry := range environment {
		if strings.IndexByte(entry, 0) >= 0 {
			return fmt.Errorf("environment: entries must not contain NUL")
		}
		name, _, ok := strings.Cut(entry, "=")
		if !ok || !validEnvironmentName(name) {
			return fmt.Errorf("environment: invalid variable name")
		}
		if _, duplicate := seen[name]; duplicate {
			return fmt.Errorf("environment: duplicate variable name %q", name)
		}
		seen[name] = struct{}{}
	}
	return nil
}

func validEnvironmentName(name string) bool {
	if name == "" {
		return false
	}
	for i := 0; i < len(name); i++ {
		c := name[i]
		if i == 0 && !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_') {
			return false
		}
		if i > 0 && !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
			(c >= '0' && c <= '9') || c == '_') {
			return false
		}
	}
	return true
}
