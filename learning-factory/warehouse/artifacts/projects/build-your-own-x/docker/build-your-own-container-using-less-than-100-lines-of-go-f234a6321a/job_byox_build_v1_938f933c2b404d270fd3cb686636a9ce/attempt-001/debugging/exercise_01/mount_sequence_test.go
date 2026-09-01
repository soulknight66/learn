package mountorder

import "testing"

func TestMountSequencePreservesNamespaceBoundary(t *testing.T) {
	want := []string{
		"make-private:/", "bind:/fixture", "set-hostname", "chroot:/fixture",
		"chdir:/", "mount-proc:/proc", "exec",
	}
	got := Steps("/fixture", true)
	if len(got) != len(want) {
		t.Fatalf("got %q, want %q", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("step %d = %q, want %q (all: %q)", i, got[i], want[i], got)
		}
	}
}
