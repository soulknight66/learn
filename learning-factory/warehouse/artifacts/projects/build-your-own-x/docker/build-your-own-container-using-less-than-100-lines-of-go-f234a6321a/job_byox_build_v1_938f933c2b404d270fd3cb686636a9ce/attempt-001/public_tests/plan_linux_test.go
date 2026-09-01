//go:build linux

package public_tests_test

import (
	"syscall"
	"testing"

	container "example.com/tinycontainer"
)

func TestLaunchPlanContainsIsolationAndIdentityMappings(t *testing.T) {
	cfg := validConfig(t)
	plan, err := container.BuildLaunchPlan(cfg, "/proc/self/exe", 1234, 2345)
	if err != nil {
		t.Fatalf("BuildLaunchPlan: %v", err)
	}
	wantFlags := uintptr(syscall.CLONE_NEWUTS | syscall.CLONE_NEWPID | syscall.CLONE_NEWNS |
		syscall.CLONE_NEWIPC | syscall.CLONE_NEWNET | syscall.CLONE_NEWUSER)
	if plan.CloneFlags != wantFlags {
		t.Fatalf("clone flags = %#x, want %#x", plan.CloneFlags, wantFlags)
	}
	if len(plan.UIDMappings) != 1 || plan.UIDMappings[0] != (container.IDMap{ContainerID: 0, HostID: 1234, Size: 1}) {
		t.Fatalf("unexpected UID map: %+v", plan.UIDMappings)
	}
	if len(plan.GIDMappings) != 1 || plan.GIDMappings[0] != (container.IDMap{ContainerID: 0, HostID: 2345, Size: 1}) {
		t.Fatalf("unexpected GID map: %+v", plan.GIDMappings)
	}
	if !plan.DisableSetgroups {
		t.Fatal("setgroups must be disabled for a single unprivileged GID mapping")
	}
	if len(plan.Arguments) == 0 || !container.IsChildInvocation(plan.Arguments) {
		t.Fatalf("plan does not re-exec the child phase: %q", plan.Arguments)
	}
}

func TestLaunchPlanWithoutUserNamespaceHasNoMappings(t *testing.T) {
	cfg := validConfig(t)
	cfg.UseUserNamespace = false
	plan, err := container.BuildLaunchPlan(cfg, "/proc/self/exe", 1234, 2345)
	if err != nil {
		t.Fatalf("BuildLaunchPlan: %v", err)
	}
	if plan.CloneFlags&uintptr(syscall.CLONE_NEWUSER) != 0 {
		t.Fatal("user namespace unexpectedly enabled")
	}
	if len(plan.UIDMappings) != 0 || len(plan.GIDMappings) != 0 || plan.DisableSetgroups {
		t.Fatalf("unexpected mapping state: %+v", plan)
	}
}
