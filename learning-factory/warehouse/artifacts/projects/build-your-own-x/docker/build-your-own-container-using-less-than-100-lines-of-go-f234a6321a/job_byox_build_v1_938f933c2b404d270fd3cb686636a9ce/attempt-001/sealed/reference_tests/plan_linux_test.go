//go:build linux

package reference_tests_test

import (
	"reflect"
	"syscall"
	"testing"

	container "example.com/tinycontainer"
)

func TestNamespaceFlags(t *testing.T) {
	base := uintptr(syscall.CLONE_NEWUTS | syscall.CLONE_NEWPID | syscall.CLONE_NEWNS |
		syscall.CLONE_NEWIPC | syscall.CLONE_NEWNET)
	withoutUser, err := container.NamespaceFlags(false)
	if err != nil {
		t.Fatal(err)
	}
	withUser, err := container.NamespaceFlags(true)
	if err != nil {
		t.Fatal(err)
	}
	if withoutUser != base || withUser != base|uintptr(syscall.CLONE_NEWUSER) {
		t.Fatalf("flags without=%#x with=%#x base=%#x", withoutUser, withUser, base)
	}
}

func TestBuildLaunchPlan(t *testing.T) {
	cfg := validConfig(t)
	plan, err := container.BuildLaunchPlan(cfg, "/proc/self/exe", 4100, 4200)
	if err != nil {
		t.Fatalf("BuildLaunchPlan: %v", err)
	}
	if plan.Executable != "/proc/self/exe" || !container.IsChildInvocation(plan.Arguments) {
		t.Fatalf("unexpected execution plan: %+v", plan)
	}
	if !reflect.DeepEqual(plan.UIDMappings, []container.IDMap{{ContainerID: 0, HostID: 4100, Size: 1}}) {
		t.Fatalf("UID mappings: %+v", plan.UIDMappings)
	}
	if !reflect.DeepEqual(plan.GIDMappings, []container.IDMap{{ContainerID: 0, HostID: 4200, Size: 1}}) {
		t.Fatalf("GID mappings: %+v", plan.GIDMappings)
	}
	if !plan.DisableSetgroups {
		t.Fatal("setgroups not disabled")
	}
}

func TestBuildLaunchPlanRejectsBadProcessInputs(t *testing.T) {
	cfg := validConfig(t)
	for _, test := range []struct {
		path     string
		uid, gid int
	}{
		{"relative", 1, 1},
		{"/unclean/../path", 1, 1},
		{"/proc/self/exe", -1, 1},
		{"/proc/self/exe", 1, -1},
	} {
		if _, err := container.BuildLaunchPlan(cfg, test.path, test.uid, test.gid); err == nil {
			t.Fatalf("accepted path=%q uid=%d gid=%d", test.path, test.uid, test.gid)
		}
	}
}
