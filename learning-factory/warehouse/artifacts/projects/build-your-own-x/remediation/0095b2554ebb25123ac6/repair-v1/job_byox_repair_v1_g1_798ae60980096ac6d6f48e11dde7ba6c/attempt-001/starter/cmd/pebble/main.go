package main

import (
	"fmt"
	"io"
	"os"

	pebble "example.com/pebble"
)

func main() {
	if err := run(os.Args[1:], os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(args []string, stdin io.Reader, stdout io.Writer) error {
	if len(args) > 1 {
		return fmt.Errorf("usage: pebble [source-file]")
	}
	var (
		source []byte
		err    error
	)
	if len(args) == 1 {
		source, err = os.ReadFile(args[0])
	} else {
		source, err = io.ReadAll(stdin)
	}
	if err != nil {
		return fmt.Errorf("read source: %w", err)
	}
	output, err := pebble.Execute(string(source))
	if err != nil {
		return err
	}
	for _, value := range output {
		if _, err := fmt.Fprintln(stdout, value); err != nil {
			return fmt.Errorf("write output: %w", err)
		}
	}
	return nil
}
