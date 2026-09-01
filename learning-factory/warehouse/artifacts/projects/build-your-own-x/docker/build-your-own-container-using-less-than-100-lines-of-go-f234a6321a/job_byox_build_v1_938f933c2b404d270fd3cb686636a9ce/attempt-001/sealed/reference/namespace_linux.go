//go:build linux

package tinycontainer

import "syscall"

func platformNamespaceFlags(useUserNamespace bool) (uintptr, error) {
	flags := uintptr(syscall.CLONE_NEWUTS | syscall.CLONE_NEWPID | syscall.CLONE_NEWNS |
		syscall.CLONE_NEWIPC | syscall.CLONE_NEWNET)
	if useUserNamespace {
		flags |= uintptr(syscall.CLONE_NEWUSER)
	}
	return flags, nil
}
