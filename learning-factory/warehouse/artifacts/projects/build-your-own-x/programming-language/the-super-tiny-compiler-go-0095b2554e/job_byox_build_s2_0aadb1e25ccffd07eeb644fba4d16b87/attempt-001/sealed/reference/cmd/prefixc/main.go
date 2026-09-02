package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	pf "example.com/prefixforge"
)

func main() {
	mode := flag.String("mode", "run", "tokens, ast, bytecode, run, or eval")
	flag.Parse()
	if flag.NArg() > 1 {
		fail(fmt.Errorf("expected at most one source argument"))
	}
	var source string
	if flag.NArg() == 1 {
		source = flag.Arg(0)
	} else {
		data, err := io.ReadAll(io.LimitReader(os.Stdin, pf.MaxSourceBytes+1))
		if err != nil {
			fail(err)
		}
		if len(data) > pf.MaxSourceBytes {
			fail(fmt.Errorf("source exceeds %d bytes", pf.MaxSourceBytes))
		}
		source = string(data)
	}
	if err := dispatch(*mode, source); err != nil {
		fail(err)
	}
}

func dispatch(mode, source string) error {
	tokens, err := pf.Tokenize(source)
	if err != nil {
		return err
	}
	if mode == "tokens" {
		return json.NewEncoder(os.Stdout).Encode(tokens)
	}
	program, err := pf.Parse(tokens)
	if err != nil {
		return err
	}
	if mode == "ast" {
		return json.NewEncoder(os.Stdout).Encode(program)
	}
	if mode == "eval" {
		value, err := pf.Evaluate(program, os.Stdout)
		if err != nil {
			return err
		}
		fmt.Printf("=> %s\n", value)
		return nil
	}
	code, err := pf.Compile(program)
	if err != nil {
		return err
	}
	if mode == "bytecode" {
		fmt.Print(code.String())
		return nil
	}
	if mode != "run" {
		return fmt.Errorf("unknown mode %q", mode)
	}
	value, err := pf.Run(code, os.Stdout)
	if err != nil {
		return err
	}
	fmt.Printf("=> %s\n", value)
	return nil
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, "prefixc:", strings.TrimSpace(err.Error()))
	os.Exit(1)
}
