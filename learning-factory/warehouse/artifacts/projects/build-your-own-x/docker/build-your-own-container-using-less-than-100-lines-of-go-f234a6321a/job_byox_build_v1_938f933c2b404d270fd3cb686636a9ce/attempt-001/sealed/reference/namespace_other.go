//go:build !linux

package tinycontainer

func platformNamespaceFlags(bool) (uintptr, error) {
	return 0, ErrNotLinux
}
