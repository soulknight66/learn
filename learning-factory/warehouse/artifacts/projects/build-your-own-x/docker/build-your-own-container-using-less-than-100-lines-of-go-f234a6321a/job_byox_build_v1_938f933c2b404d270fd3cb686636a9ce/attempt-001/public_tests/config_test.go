package public_tests_test

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"

	container "example.com/tinycontainer"
)

func validConfig(t *testing.T) container.Config {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "proc"), 0o755); err != nil {
		t.Fatal(err)
	}
	cfg := container.DefaultConfig()
	cfg.RootFS = root
	cfg.Command = []string{"/bin/probe", "hello world"}
	cfg.Environment = []string{"PATH=/bin", "MESSAGE=a=b"}
	return cfg
}

func TestDefaultConfigReturnsIndependentEnvironment(t *testing.T) {
	a := container.DefaultConfig()
	b := container.DefaultConfig()
	if a.Hostname != "tinybox" || !a.MountProc || !a.UseUserNamespace {
		t.Fatalf("unsafe or unexpected defaults: %+v", a)
	}
	a.Environment[0] = "CHANGED=yes"
	if reflect.DeepEqual(a.Environment, b.Environment) {
		t.Fatal("DefaultConfig reused mutable environment storage")
	}
}

func TestValidateConfigAcceptsWellFormedInput(t *testing.T) {
	if err := container.ValidateConfig(validConfig(t)); err != nil {
		t.Fatalf("valid configuration rejected: %v", err)
	}
}

func TestValidateConfigRejectsDangerousRootsAndCommands(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*container.Config)
	}{
		{"host root", func(c *container.Config) { c.RootFS = "/" }},
		{"relative root", func(c *container.Config) { c.RootFS = "rootfs" }},
		{"unclean root", func(c *container.Config) { c.RootFS += "/../" + filepath.Base(c.RootFS) }},
		{"empty command", func(c *container.Config) { c.Command = nil }},
		{"relative executable", func(c *container.Config) { c.Command[0] = "bin/probe" }},
		{"bad hostname", func(c *container.Config) { c.Hostname = "-bad" }},
		{"duplicate environment", func(c *container.Config) { c.Environment = []string{"A=1", "A=2"} }},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg := validConfig(t)
			tt.mutate(&cfg)
			if err := container.ValidateConfig(cfg); err == nil {
				t.Fatal("invalid configuration accepted")
			}
		})
	}
}

func TestChildArgumentsRoundTripWithoutShellParsing(t *testing.T) {
	want := validConfig(t)
	want.Hostname = "node-7.lab"
	want.UseUserNamespace = false
	want.MountProc = false
	want.Command = []string{"/bin/probe", "contains spaces", "$(not-a-shell)"}
	want.Environment = []string{"EMPTY=", "EQUALS=a=b", "TEXT=two words"}

	args := container.EncodeChildArgs(want)
	if !container.IsChildInvocation(args) {
		t.Fatalf("encoded argv does not start with the internal marker: %q", args)
	}
	got, err := container.ParseChildArgs(args)
	if err != nil {
		t.Fatalf("ParseChildArgs: %v", err)
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("round trip mismatch\n got: %#v\nwant: %#v", got, want)
	}
}

func TestParseRunArgsAppliesDefaults(t *testing.T) {
	cfg := validConfig(t)
	got, err := container.ParseRunArgs([]string{"run", "--rootfs", cfg.RootFS, "--", "/bin/probe", "x"})
	if err != nil {
		t.Fatalf("ParseRunArgs: %v", err)
	}
	if got.Hostname != "tinybox" || !got.MountProc || !got.UseUserNamespace {
		t.Fatalf("defaults were not applied: %+v", got)
	}
	if !reflect.DeepEqual(got.Command, []string{"/bin/probe", "x"}) {
		t.Fatalf("command changed: %q", got.Command)
	}
}
