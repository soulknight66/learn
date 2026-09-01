//go:build linux

package reference_tests_test

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"testing"
	"time"

	container "example.com/tinycontainer"
)

func TestMain(m *testing.M) {
	if container.IsChildInvocation(os.Args[1:]) {
		if err := container.RunChildInvocation(os.Args[1:]); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(125)
		}
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func TestIntegrationProbe(t *testing.T) {
	rootfs := os.Getenv("TINYCONTAINER_INTEGRATION_ROOTFS")
	if rootfs == "" {
		t.Skip("set TINYCONTAINER_INTEGRATION_ROOTFS on a disposable Linux host")
	}
	useUserNamespace := true
	if raw := os.Getenv("TINYCONTAINER_INTEGRATION_USERNS"); raw != "" {
		parsed, err := strconv.ParseBool(raw)
		if err != nil {
			t.Fatalf("TINYCONTAINER_INTEGRATION_USERNS: %v", err)
		}
		useUserNamespace = parsed
	}

	cfg := container.DefaultConfig()
	cfg.RootFS = rootfs
	cfg.Hostname = "integration-box"
	cfg.Command = []string{"/bin/probe"}
	cfg.Environment = []string{"PATH=/bin", "CHECK=isolated"}
	cfg.UseUserNamespace = useUserNamespace

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	var stdout, stderr bytes.Buffer
	err := container.Run(ctx, cfg, container.IO{Stdout: &stdout, Stderr: &stderr})
	if err != nil {
		t.Fatalf("Run: %v\nstderr: %s", err, stderr.String())
	}
	output := stdout.String()
	for _, want := range []string{"hostname=integration-box", "pid=1", "proc=mounted", "CHECK=isolated"} {
		if !strings.Contains(output, want) {
			t.Fatalf("output missing %q:\n%s", want, output)
		}
	}

	cfg.Command = []string{"/bin/probe", "--exit", "17"}
	err = container.Run(ctx, cfg, container.IO{Stderr: &stderr})
	var processExit *container.ExitError
	if !errors.As(err, &processExit) || processExit.Code != 17 {
		t.Fatalf("exit result = %v, want ExitError(17)", err)
	}
}
