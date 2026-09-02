package prefixforge

import (
	"errors"
	"io"
)

// ErrNotImplemented marks the intentionally incomplete learner stages.
var ErrNotImplemented = errors.New("prefixforge: stage not implemented")

func Tokenize(source string) ([]Token, error) {
	return nil, ErrNotImplemented
}

func Parse(tokens []Token) (Program, error) {
	return Program{}, ErrNotImplemented
}

func Check(program Program) ([]ValueType, error) {
	return nil, ErrNotImplemented
}

func Compile(program Program) (Bytecode, error) {
	return Bytecode{}, ErrNotImplemented
}

func Run(code Bytecode, out io.Writer) (Value, error) {
	return Value{}, ErrNotImplemented
}

func Evaluate(program Program, out io.Writer) (Value, error) {
	return Value{}, ErrNotImplemented
}

func Execute(source string, out io.Writer) (Value, error) {
	tokens, err := Tokenize(source)
	if err != nil {
		return Value{}, err
	}
	program, err := Parse(tokens)
	if err != nil {
		return Value{}, err
	}
	code, err := Compile(program)
	if err != nil {
		return Value{}, err
	}
	return Run(code, out)
}
