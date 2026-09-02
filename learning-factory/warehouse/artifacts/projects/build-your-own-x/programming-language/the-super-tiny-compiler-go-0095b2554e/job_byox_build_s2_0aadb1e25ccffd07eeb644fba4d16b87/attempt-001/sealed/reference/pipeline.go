package prefixforge

import "io"

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
