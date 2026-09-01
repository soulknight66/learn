package adversarial_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	container "example.com/tinycontainer"
)

func baseConfig(t *testing.T) container.Config {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "proc"), 0o755); err != nil {
		t.Fatal(err)
	}
	cfg := container.DefaultConfig()
	cfg.RootFS = root
	cfg.Command = []string{"/bin/probe"}
	return cfg
}

func TestHostnamesAtAndAcrossBoundary(t *testing.T) {
	cfg := baseConfig(t)
	cfg.Hostname = strings.Repeat("a", 63)
	if err := container.ValidateConfig(cfg); err != nil {
		t.Fatalf("63-byte hostname rejected: %v", err)
	}
	for _, hostname := range []string{strings.Repeat("a", 64), "a.", ".a", "a_b", "a/b", "é"} {
		cfg.Hostname = hostname
		if err := container.ValidateConfig(cfg); err == nil {
			t.Fatalf("invalid hostname accepted: %q", hostname)
		}
	}
}

func TestEnvironmentNameAndValueBoundaries(t *testing.T) {
	cfg := baseConfig(t)
	for _, environment := range [][]string{
		{"=value"}, {"A-B=value"}, {"A"}, {"A=ok", "A=again"}, {"A=bad\x00value"},
	} {
		cfg.Environment = environment
		if err := container.ValidateConfig(cfg); err == nil {
			t.Fatalf("invalid environment accepted: %q", environment)
		}
	}
	cfg.Environment = []string{"_A=", "A0=a=b=c"}
	if err := container.ValidateConfig(cfg); err != nil {
		t.Fatalf("valid environment rejected: %v", err)
	}
}

func TestProcSymlinkRejected(t *testing.T) {
	cfg := baseConfig(t)
	if err := os.Remove(filepath.Join(cfg.RootFS, "proc")); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink("/proc", filepath.Join(cfg.RootFS, "proc")); err != nil {
		t.Fatal(err)
	}
	if err := container.ValidateConfig(cfg); err == nil {
		t.Fatal("symbolic-link proc mountpoint accepted")
	}
}

func TestMalformedInternalInvocationRejected(t *testing.T) {
	cfg := baseConfig(t)
	args := container.EncodeChildArgs(cfg)
	for i, arg := range args {
		if strings.HasPrefix(arg, "--error-fd=") {
			args[i] = "--error-fd=9"
			break
		}
	}
	if _, err := container.ParseChildArgs(args); err == nil {
		t.Fatal("arbitrary setup descriptor accepted")
	}
}
