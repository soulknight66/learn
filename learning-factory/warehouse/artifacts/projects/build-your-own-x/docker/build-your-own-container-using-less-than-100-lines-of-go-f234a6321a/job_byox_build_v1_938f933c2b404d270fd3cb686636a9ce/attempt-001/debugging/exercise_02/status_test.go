package exitstatus

import "testing"

func TestStatus(t *testing.T) {
	for _, test := range []struct {
		name             string
		exitCode, signal int
		want             int
	}{
		{"success", 0, 0, 0},
		{"ordinary failure", 17, 0, 17},
		{"terminated", -1, 15, 143},
		{"killed", -1, 9, 137},
	} {
		t.Run(test.name, func(t *testing.T) {
			if got := Status(test.exitCode, test.signal); got != test.want {
				t.Fatalf("Status(%d, %d) = %d, want %d", test.exitCode, test.signal, got, test.want)
			}
		})
	}
}
