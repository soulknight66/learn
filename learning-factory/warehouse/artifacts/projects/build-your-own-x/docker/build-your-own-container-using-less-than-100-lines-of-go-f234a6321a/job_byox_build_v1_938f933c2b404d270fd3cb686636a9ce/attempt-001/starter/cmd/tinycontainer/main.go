package main

import (
	"context"
	"errors"
	"fmt"
	"os"

	container "example.com/tinycontainer"
)

func main() {
	if container.IsChildInvocation(os.Args[1:]) {
		if err := container.RunChildInvocation(os.Args[1:]); err != nil {
			fmt.Fprintf(os.Stderr, "tinycontainer child setup: %v\n", err)
			os.Exit(125)
		}
		return
	}

	cfg, err := container.ParseRunArgs(os.Args[1:])
	if err != nil {
		fmt.Fprintf(os.Stderr, "usage: tinycontainer run --rootfs PATH [options] -- /absolute/command [args...]\nerror: %v\n", err)
		os.Exit(2)
	}

	err = container.Run(context.Background(), cfg, container.IO{
		Stdin:  os.Stdin,
		Stdout: os.Stdout,
		Stderr: os.Stderr,
	})
	if err == nil {
		return
	}

	var processExit *container.ExitError
	if errors.As(err, &processExit) {
		os.Exit(processExit.Code)
	}
	fmt.Fprintf(os.Stderr, "tinycontainer run: %v\n", err)
	os.Exit(125)
}
