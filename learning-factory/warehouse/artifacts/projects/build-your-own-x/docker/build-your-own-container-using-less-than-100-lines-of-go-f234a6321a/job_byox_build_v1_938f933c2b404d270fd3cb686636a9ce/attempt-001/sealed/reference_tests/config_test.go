package reference_tests_test

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	container "example.com/tinycontainer"
)

func validConfig(t testing.TB) container.Config {
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

func TestDefaultConfigDoesNotAliasEnvironment(t *testing.T) {
	a := container.DefaultConfig()
	b := container.DefaultConfig()
	a.Environment[0] = "BROKEN=yes"
	if reflect.DeepEqual(a.Environment, b.Environment) {
		t.Fatal("default environments share backing storage")
	}
}

func TestValidateConfigAcceptsValidConfiguration(t *testing.T) {
	if err := container.ValidateConfig(validConfig(t)); err != nil {
		t.Fatalf("ValidateConfig: %v", err)
	}
}

func TestValidateConfigRejectsInvalidInputs(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*container.Config, *testing.T)
		part   string
	}{
		{"empty root", func(c *container.Config, _ *testing.T) { c.RootFS = "" }, "rootfs"},
		{"relative root", func(c *container.Config, _ *testing.T) { c.RootFS = "rootfs" }, "rootfs"},
		{"unclean root", func(c *container.Config, _ *testing.T) { c.RootFS += "/." }, "rootfs"},
		{"host root", func(c *container.Config, _ *testing.T) { c.RootFS = "/" }, "rootfs"},
		{"root symlink", func(c *container.Config, t *testing.T) {
			link := filepath.Join(t.TempDir(), "link")
			if err := os.Symlink(c.RootFS, link); err != nil {
				t.Fatal(err)
			}
			c.RootFS = link
		}, "rootfs"},
		{"missing proc", func(c *container.Config, t *testing.T) { c.RootFS = t.TempDir() }, "proc"},
		{"empty hostname", func(c *container.Config, _ *testing.T) { c.Hostname = "" }, "hostname"},
		{"empty label", func(c *container.Config, _ *testing.T) { c.Hostname = "a..b" }, "hostname"},
		{"leading hyphen", func(c *container.Config, _ *testing.T) { c.Hostname = "-node" }, "hostname"},
		{"non ASCII", func(c *container.Config, _ *testing.T) { c.Hostname = "nød" }, "hostname"},
		{"no command", func(c *container.Config, _ *testing.T) { c.Command = nil }, "command"},
		{"relative executable", func(c *container.Config, _ *testing.T) { c.Command[0] = "bin/probe" }, "command"},
		{"unclean executable", func(c *container.Config, _ *testing.T) { c.Command[0] = "/bin/../bin/probe" }, "command"},
		{"argument NUL", func(c *container.Config, _ *testing.T) { c.Command = append(c.Command, "a\x00b") }, "command"},
		{"environment without equals", func(c *container.Config, _ *testing.T) { c.Environment = []string{"NAME"} }, "environment"},
		{"environment bad name", func(c *container.Config, _ *testing.T) { c.Environment = []string{"1NAME=x"} }, "environment"},
		{"environment duplicate", func(c *container.Config, _ *testing.T) { c.Environment = []string{"A=1", "A=2"} }, "environment"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg := validConfig(t)
			tt.mutate(&cfg, t)
			err := container.ValidateConfig(cfg)
			if err == nil || !strings.Contains(err.Error(), tt.part) {
				t.Fatalf("error = %v, want one containing %q", err, tt.part)
			}
		})
	}
}

func TestChildCodecRoundTripsAllFields(t *testing.T) {
	tests := []container.Config{validConfig(t), validConfig(t)}
	tests[0].MountProc = false
	tests[0].UseUserNamespace = false
	tests[0].Command = []string{"/bin/probe", "two words", "$(literal)"}
	tests[0].Environment = []string{"EMPTY=", "EQUALS=a=b", "TEXT=two words"}
	tests[1].Environment = nil

	for _, want := range tests {
		args := container.EncodeChildArgs(want)
		got, err := container.ParseChildArgs(args)
		if err != nil {
			t.Fatalf("ParseChildArgs(%q): %v", args, err)
		}
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("round trip mismatch\n got: %#v\nwant: %#v", got, want)
		}
	}
}

func TestParseRunArgsAndMarker(t *testing.T) {
	cfg := validConfig(t)
	args := []string{"run", "--rootfs", cfg.RootFS, "--hostname", "lab-1", "--mount-proc=false",
		"--userns=false", "--env", "A=two words", "--", "/bin/probe", "x"}
	got, err := container.ParseRunArgs(args)
	if err != nil {
		t.Fatalf("ParseRunArgs: %v", err)
	}
	if got.Hostname != "lab-1" || got.MountProc || got.UseUserNamespace {
		t.Fatalf("flags not applied: %+v", got)
	}
	if !reflect.DeepEqual(got.Environment, []string{"A=two words"}) {
		t.Fatalf("environment = %q", got.Environment)
	}
	if container.IsChildInvocation([]string{"run"}) || container.IsChildInvocation(nil) {
		t.Fatal("public arguments mistaken for child invocation")
	}
	if _, err := container.ParseChildArgs([]string{"run"}); err == nil {
		t.Fatal("ParseChildArgs accepted a public invocation")
	}
}
